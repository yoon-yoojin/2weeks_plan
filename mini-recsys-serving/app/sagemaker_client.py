"""SageMaker real-time endpoint 호출 레이어.

FastAPI → SageMaker 내부 통신을 담당한다.
timeout과 5xx는 fallback 신호로 처리하기 위해 전용 예외로 변환한다.

환경 변수:
  AWS_REGION              - AWS 리전 (기본값: ap-northeast-2)
  SAGEMAKER_ENDPOINT_NAME - invoke 대상 endpoint 이름
"""
import json
import logging
import os
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError

from app.schemas import SageMakerRequest, SageMakerResponse

logger = logging.getLogger(__name__)

_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
_ENDPOINT_NAME = os.getenv("SAGEMAKER_ENDPOINT_NAME", "recsys-endpoint")

# endpoint 호출 timeout 설정.
# retry는 서비스 레이어(recommender.py)가 fallback으로 처리하므로 max_attempts=0.
_BOTO_CONFIG = Config(
    connect_timeout=3,
    read_timeout=5,
    retries={"max_attempts": 0},
)


# recommender.py에서 fallback 분기 판단에 사용하는 전용 예외
class EndpointTimeoutError(Exception):
    """SageMaker endpoint가 read_timeout 내에 응답하지 않음"""


class EndpointInvokeError(Exception):
    """SageMaker endpoint 5xx 또는 invoke 오류"""


class SageMakerClient:
    def __init__(self):
        # sagemaker-runtime: 모델 endpoint invoke 전용 클라이언트 (sagemaker와 별개)
        self._runtime = boto3.client(
            "sagemaker-runtime",
            region_name=_REGION,
            config=_BOTO_CONFIG,
        )

    def score(self, request: SageMakerRequest) -> SageMakerResponse:
        """SageMaker endpoint에 scoring 요청을 보내고 응답을 파싱한다.

        timeout → EndpointTimeoutError
        5xx / invoke 실패 → EndpointInvokeError
        두 예외 모두 recommender.py에서 fallback으로 처리된다.
        """
        try:
            response = self._runtime.invoke_endpoint(
                EndpointName=_ENDPOINT_NAME,
                ContentType="application/json",
                Body=request.model_dump_json(),
            )
        except ReadTimeoutError:
            # endpoint가 read_timeout(5s) 내에 응답하지 못한 경우
            logger.warning("SageMaker endpoint timeout: request_id=%s", request.request_id)
            raise EndpointTimeoutError()
        except ClientError as e:
            # endpoint 자체 오류 (5xx, 서비스 일시 불가 등)
            logger.error("SageMaker invoke_endpoint failed: %s", e)
            raise EndpointInvokeError()

        body = json.loads(response["Body"].read())
        return SageMakerResponse(**body)

    def check_connection(self) -> bool:
        """/ready 엔드포인트용: endpoint describe로 SageMaker 접근 가능 여부를 확인한다.
        sagemaker-runtime이 아닌 sagemaker 클라이언트로 describe_endpoint를 호출한다.
        """
        try:
            sm = boto3.client("sagemaker", region_name=_REGION)
            sm.describe_endpoint(EndpointName=_ENDPOINT_NAME)
            return True
        except Exception:
            return False


# 모듈 수준 싱글턴
sagemaker_client = SageMakerClient()
