class AppError(Exception):
    """서비스 정의 에러의 base class. status_code와 error code를 함께 보관한다."""
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BadRequestError(AppError):
    """서비스 정책상 처리할 수 없는 요청 (400)"""
    def __init__(self, message: str = "Bad request"):
        super().__init__(
            code="BAD_REQUEST",
            message=message,
            status_code=400,
        )


# [변경] ModelNotReadyError 삭제: 서비스 API는 로컬 모델을 보유하지 않는다.
# 대신 외부 의존성 장애를 나타내는 에러 두 개로 교체.

class SequenceStoreUnavailableError(AppError):
    """DynamoDB 접근 불가 (503) — 유저 시퀀스/후보군 조회 실패"""
    def __init__(self):
        super().__init__(
            code="SEQUENCE_STORE_UNAVAILABLE",
            message="User data store is temporarily unavailable",
            status_code=503,
        )


class MLEndpointUnavailableError(AppError):
    """SageMaker endpoint invoke 자체가 불가능한 경우 (503)
    timeout/5xx는 fallback으로 처리하고, 클라이언트 연결 자체가 실패할 때 이 에러를 사용한다."""
    def __init__(self):
        super().__init__(
            code="ML_ENDPOINT_UNAVAILABLE",
            message="Temporary recommendation dependency failure",
            status_code=503,
        )
