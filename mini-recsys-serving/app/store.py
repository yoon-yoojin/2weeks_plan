"""DynamoDB 조회 레이어.

user_sequences 테이블: 유저 최근 행동 시퀀스
candidate_sets 테이블: 유저별 scoring 후보군

환경 변수:
  AWS_REGION                     - AWS 리전 (기본값: ap-northeast-2)
  DYNAMODB_USER_SEQUENCES_TABLE  - user sequences 테이블명
  DYNAMODB_CANDIDATE_SETS_TABLE  - candidate sets 테이블명
"""
import os
import logging
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError

from app.errors import SequenceStoreUnavailableError

logger = logging.getLogger(__name__)

# 환경 변수에서 설정을 주입받는다. 기본값은 로컬 실습용.
_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
_SEQ_TABLE_NAME = os.getenv("DYNAMODB_USER_SEQUENCES_TABLE", "user_sequences")
_CAND_TABLE_NAME = os.getenv("DYNAMODB_CANDIDATE_SETS_TABLE", "candidate_sets")


class DynamoDBStore:
    def __init__(self):
        # boto3 resource: Table 객체를 통해 고수준 DynamoDB 연산을 수행한다.
        dynamodb = boto3.resource("dynamodb", region_name=_REGION)
        self._seq_table = dynamodb.Table(_SEQ_TABLE_NAME)
        self._cand_table = dynamodb.Table(_CAND_TABLE_NAME)

    def get_sequence(self, user_id: str) -> Optional[List[int]]:
        """user_sequences 테이블에서 유저 행동 시퀀스를 조회한다.

        partition key: user_id
        반환: sequence 리스트, 없으면 None (cold start 처리 필요)
        DynamoDB가 응답하지 않으면 SequenceStoreUnavailableError(503)를 발생시킨다.
        """
        try:
            response = self._seq_table.get_item(Key={"user_id": user_id})
        except ClientError as e:
            logger.error("DynamoDB get_sequence failed: %s", e)
            raise SequenceStoreUnavailableError()

        item = response.get("Item")
        if not item:
            return None

        # DynamoDB는 숫자를 Decimal로 반환하므로 int로 변환한다.
        return [int(x) for x in item.get("sequence", [])]

    def get_candidates(self, user_id: str) -> Optional[List[int]]:
        """candidate_sets 테이블에서 scoring 후보군을 조회한다.

        partition key: candidate_key = "user#{user_id}"
        반환: candidate_item_ids 리스트, 없으면 None (missing_candidates 처리 필요)
        DynamoDB가 응답하지 않으면 SequenceStoreUnavailableError(503)를 발생시킨다.
        """
        try:
            candidate_key = f"user#{user_id}"
            response = self._cand_table.get_item(Key={"candidate_key": candidate_key})
        except ClientError as e:
            logger.error("DynamoDB get_candidates failed: %s", e)
            raise SequenceStoreUnavailableError()

        item = response.get("Item")
        if not item:
            return None

        return [int(x) for x in item.get("candidate_item_ids", [])]

    def check_connection(self) -> bool:
        """/ready 엔드포인트용: DynamoDB 테이블 접근 가능 여부를 확인한다.
        table.load()는 내부적으로 describe_table을 호출한다.
        """
        try:
            self._seq_table.load()
            return True
        except Exception:
            return False


# 모듈 수준 싱글턴: 앱 전체에서 하나의 클라이언트를 공유한다.
store = DynamoDBStore()
