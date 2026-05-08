"""
SageMaker Processing Job: YOOCHOOSE 클릭 로그 전처리

[입력]
  /opt/ml/processing/input/clicks/yoochoose-clicks.dat

[S3 출력]
  /opt/ml/processing/output/train/train.parquet   - integer id 기반 학습 시퀀스
  /opt/ml/processing/output/valid/valid.parquet   - integer id 기반 검증 시퀀스
  /opt/ml/processing/output/test/test.parquet     - integer id 기반 평가 시퀀스
  /opt/ml/processing/output/meta/item2id.json     - goodsno → integer id
  /opt/ml/processing/output/meta/id2item.json     - integer id → goodsno

[DynamoDB 출력]
  user_sequences  테이블: test set 시퀀스 (goodsno 기반)
  candidate_sets  테이블: 인기 상품 후보군 (goodsno 기반)

[설계 원칙]
  - parquet은 integer id로 저장 (Training Job 입력)
  - DynamoDB는 goodsno로 저장 (서비스 API와 ML 내부 구조 분리)
  - 매퍼(item2id/id2item)는 Training Job이 model.tar.gz에 번들
"""
import os
import json
import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import boto3
import pandas as pd
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# SageMaker Processing Job 경로 규약
INPUT_DIR = "/opt/ml/processing/input/clicks"
OUTPUT_TRAIN_DIR = "/opt/ml/processing/output/train"
OUTPUT_VALID_DIR = "/opt/ml/processing/output/valid"
OUTPUT_TEST_DIR = "/opt/ml/processing/output/test"
OUTPUT_META_DIR = "/opt/ml/processing/output/meta"

CLICKS_COLS = ["session_id", "timestamp", "item_id", "category"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-session-len", type=int, default=4,
                        help="유효 세션 최소 클릭 수 (train/valid/test 분리에 최소 4 필요)")
    parser.add_argument("--min-item-freq", type=int, default=5,
                        help="유효 아이템 최소 등장 횟수")
    parser.add_argument("--candidate-size", type=int, default=200,
                        help="DynamoDB에 적재할 인기 후보군 크기")
    parser.add_argument("--seq-table", type=str, default="user_sequences")
    parser.add_argument("--cand-table", type=str, default="candidate_sets")
    parser.add_argument("--aws-region", type=str, default="ap-northeast-2")
    return parser.parse_args()


# ── 1. 데이터 로드 ──────────────────────────────────────────────

def load_clicks(input_dir: str) -> pd.DataFrame:
    path = os.path.join(input_dir, "yoochoose-clicks.dat")
    df = pd.read_csv(
        path,
        header=None,
        names=CLICKS_COLS,
        dtype={"session_id": "int64", "item_id": "int64", "category": "str"},
        parse_dates=["timestamp"],
    )
    logger.info("클릭 로그 로드: %d rows", len(df))
    return df


# ── 2. 필터링 및 시퀀스 생성 ────────────────────────────────────

def build_sequences(df: pd.DataFrame, min_session_len: int, min_item_freq: int) -> Tuple[pd.DataFrame, pd.Series]:
    item_freq = df["item_id"].value_counts()
    valid_items = item_freq[item_freq >= min_item_freq].index
    df = df[df["item_id"].isin(valid_items)]

    df = df.sort_values(["session_id", "timestamp"])
    sequences = (
        df.groupby("session_id")["item_id"]
        .apply(list)
        .reset_index()
        .rename(columns={"item_id": "item_ids"})
    )
    sequences = sequences[sequences["item_ids"].map(len) >= min_session_len].reset_index(drop=True)

    logger.info("필터 후 세션 수: %d / 유니크 아이템: %d", len(sequences), len(valid_items))
    return sequences, item_freq


# ── 3. goodsno → integer id 매핑 생성 ──────────────────────────

def build_item_mapping(sequences: pd.DataFrame) -> Tuple[Dict, Dict]:
    all_items = [item for seq in sequences["item_ids"] for item in seq]
    freq = pd.Series(all_items).value_counts()

    # 0은 padding 예약, 1부터 시작
    item2id: Dict[int, int] = {int(item): idx + 1 for idx, item in enumerate(freq.index)}
    id2item: Dict[int, int] = {v: k for k, v in item2id.items()}

    logger.info("매핑 생성 완료: %d 아이템", len(item2id))
    return item2id, id2item


# ── 4. leave-one-out split ──────────────────────────────────────

def split_sequences(sequences: pd.DataFrame, item2id: Dict) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    각 세션 [i1, i2, ..., in] 에서:
      train: item_ids=[i1..i(n-2)], label=i(n-1)
      valid: item_ids=[i1..i(n-1)], label=i(n)
      test:  item_ids=[i1..in] (integer id), goodsno_seq=[g1..gn] (DynamoDB용)
    """
    train_rows, valid_rows, test_rows = [], [], []

    for _, row in sequences.iterrows():
        session_id = int(row["session_id"])
        goodsno_seq = [int(x) for x in row["item_ids"]]
        int_seq = [item2id[g] for g in goodsno_seq if g in item2id]

        if len(int_seq) < 4:
            continue

        train_rows.append({"session_id": session_id, "item_ids": int_seq[:-2], "label": int_seq[-2]})
        valid_rows.append({"session_id": session_id, "item_ids": int_seq[:-1], "label": int_seq[-1]})
        test_rows.append({"session_id": session_id, "item_ids": int_seq, "goodsno_seq": goodsno_seq})

    train_df = pd.DataFrame(train_rows)
    valid_df = pd.DataFrame(valid_rows)
    test_df = pd.DataFrame(test_rows)

    logger.info("split 완료 — train: %d / valid: %d / test: %d", len(train_df), len(valid_df), len(test_df))
    return train_df, valid_df, test_df


# ── 5. 저장 ─────────────────────────────────────────────────────

def save_parquets(train_df: pd.DataFrame, valid_df: pd.DataFrame, test_df: pd.DataFrame) -> None:
    for dir_path in [OUTPUT_TRAIN_DIR, OUTPUT_VALID_DIR, OUTPUT_TEST_DIR]:
        os.makedirs(dir_path, exist_ok=True)

    train_df[["session_id", "item_ids", "label"]].to_parquet(
        os.path.join(OUTPUT_TRAIN_DIR, "train.parquet"), index=False
    )
    valid_df[["session_id", "item_ids", "label"]].to_parquet(
        os.path.join(OUTPUT_VALID_DIR, "valid.parquet"), index=False
    )
    test_df[["session_id", "item_ids"]].to_parquet(
        os.path.join(OUTPUT_TEST_DIR, "test.parquet"), index=False
    )
    logger.info("parquet 저장 완료")


def save_meta(item2id: Dict, id2item: Dict) -> None:
    os.makedirs(OUTPUT_META_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_META_DIR, "item2id.json"), "w") as f:
        json.dump({str(k): v for k, v in item2id.items()}, f)
    with open(os.path.join(OUTPUT_META_DIR, "id2item.json"), "w") as f:
        json.dump({str(k): v for k, v in id2item.items()}, f)
    logger.info("매퍼 저장 완료: item2id / id2item")


# ── 6. DynamoDB 적재 ─────────────────────────────────────────────

def _batch_write(table, items: List[Dict]) -> None:
    with table.batch_writer() as writer:
        for item in items:
            writer.put_item(Item=item)


def upload_to_dynamodb(
    test_df: pd.DataFrame,
    item_freq: pd.Series,
    candidate_size: int,
    seq_table_name: str,
    cand_table_name: str,
    region: str,
) -> None:
    dynamodb = boto3.resource("dynamodb", region_name=region)
    seq_table = dynamodb.Table(seq_table_name)
    cand_table = dynamodb.Table(cand_table_name)
    now = datetime.now(timezone.utc).isoformat()

    # user_sequences: goodsno 시퀀스로 적재 (ML 내부 integer id 노출 없음)
    seq_items = [
        {
            "user_id": str(row["session_id"]),
            "sequence": [int(g) for g in row["goodsno_seq"]],
            "updated_at": now,
        }
        for _, row in test_df.iterrows()
    ]
    _batch_write(seq_table, seq_items)
    logger.info("user_sequences 적재 완료: %d건", len(seq_items))

    # candidate_sets: 전체 유저에 동일한 인기 상품 top-N (goodsno 기반)
    top_candidates = [int(x) for x in item_freq.head(candidate_size).index.tolist()]
    cand_items = [
        {
            "candidate_key": f"user#{row['session_id']}",
            "candidate_item_ids": top_candidates,
            "updated_at": now,
        }
        for _, row in test_df.iterrows()
    ]
    _batch_write(cand_table, cand_items)
    logger.info("candidate_sets 적재 완료: %d건", len(cand_items))


# ── main ─────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    logger.info("args: %s", vars(args))

    df = load_clicks(INPUT_DIR)
    sequences, item_freq = build_sequences(df, args.min_session_len, args.min_item_freq)
    item2id, id2item = build_item_mapping(sequences)
    train_df, valid_df, test_df = split_sequences(sequences, item2id)

    save_parquets(train_df, valid_df, test_df)
    save_meta(item2id, id2item)
    upload_to_dynamodb(
        test_df, item_freq,
        args.candidate_size,
        args.seq_table,
        args.cand_table,
        args.aws_region,
    )

    logger.info("전처리 완료")


if __name__ == "__main__":
    main()
