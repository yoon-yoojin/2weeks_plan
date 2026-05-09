"""
SageMaker Processing Job 제출 스크립트

실행:
  python sagemaker/run_preprocessing.py

환경 변수:
  SAGEMAKER_ROLE_ARN   - SageMaker 실행 IAM Role ARN (필수)
  AWS_REGION           - AWS 리전 (기본값: ap-northeast-2)

S3 경로 (s3://2weekplan):
  코드:  sagemaker/preprocess.py
  입력:  raw/yoochoose/yoochoose-clicks.dat
  출력:  gsasrec/input/train|valid|test/
         gsasrec/meta/item2id.json, id2item.json
"""
import os
import argparse

import boto3
import sagemaker
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput

BUCKET = "2weekplan"
REGION = os.getenv("AWS_REGION", "ap-northeast-2")
ROLE_ARN = os.getenv("SAGEMAKER_ROLE_ARN")

S3_SCRIPT_PATH = f"s3://{BUCKET}/sagemaker/preprocess.py"

S3_RAW_INPUT   = f"s3://{BUCKET}/raw/yoochoose/"
S3_TRAIN_OUT   = f"s3://{BUCKET}/gsasrec/input/train/"
S3_VALID_OUT   = f"s3://{BUCKET}/gsasrec/input/valid/"
S3_TEST_OUT    = f"s3://{BUCKET}/gsasrec/input/test/"
S3_META_OUT    = f"s3://{BUCKET}/gsasrec/meta/"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-session-len", type=int, default=4)
    parser.add_argument("--min-item-freq",   type=int, default=5)
    parser.add_argument("--candidate-size",  type=int, default=200)
    parser.add_argument("--seq-table",  type=str, default="user_sequences")
    parser.add_argument("--cand-table", type=str, default="candidate_sets")
    parser.add_argument("--instance-type", type=str, default="ml.m5.xlarge")
    return parser.parse_args()


def main() -> None:
    if not ROLE_ARN:
        raise EnvironmentError("SAGEMAKER_ROLE_ARN 환경 변수를 설정해주세요.")

    args = parse_args()

    processor = SKLearnProcessor(
        framework_version="1.2-1",
        instance_type=args.instance_type,
        instance_count=1,
        role=ROLE_ARN,
        region_name=REGION,
        base_job_name="yoochoose-preprocess",
    )

    processor.run(
        code=S3_SCRIPT_PATH,
        inputs=[
            ProcessingInput(
                source=S3_RAW_INPUT,
                destination="/opt/ml/processing/input/clicks",
            )
        ],
        outputs=[
            ProcessingOutput(
                output_name="train",
                source="/opt/ml/processing/output/train",
                destination=S3_TRAIN_OUT,
            ),
            ProcessingOutput(
                output_name="valid",
                source="/opt/ml/processing/output/valid",
                destination=S3_VALID_OUT,
            ),
            ProcessingOutput(
                output_name="test",
                source="/opt/ml/processing/output/test",
                destination=S3_TEST_OUT,
            ),
            ProcessingOutput(
                output_name="meta",
                source="/opt/ml/processing/output/meta",
                destination=S3_META_OUT,
            ),
        ],
        arguments=[
            "--min-session-len", str(args.min_session_len),
            "--min-item-freq",   str(args.min_item_freq),
            "--candidate-size",  str(args.candidate_size),
            "--seq-table",       args.seq_table,
            "--cand-table",      args.cand_table,
            "--aws-region",      REGION,
        ],
        wait=True,
        logs=True,
    )


if __name__ == "__main__":
    main()
