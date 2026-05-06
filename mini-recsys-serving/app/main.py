import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.store import store
from app.sagemaker_client import sagemaker_client
from app.recommender import recommend_service, MODEL_VERSION
from app.schemas import (
    ErrorResponse,
    HealthResponse,
    ReadyResponse,
    RecommendRequest,
    RecommendResponse,
)

logger = logging.getLogger(__name__)


# [변경] lifespan에서 로컬 모델 로딩 제거.
# 서비스 API는 DynamoDB/SageMaker를 외부에서 호출하므로 별도 로딩 단계가 없다.
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Service API starting up")
    yield
    logger.info("Service API shutting down")


app = FastAPI(lifespan=lifespan)


# ============================================================
# Exception Handlers
# ============================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Pydantic validation 실패: 필드 타입 오류, 필수값 누락, enum/range 위반 등
    logger.warning("Validation error: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="VALIDATION_ERROR",
            message="Request validation failed",
        ).model_dump(),
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    # 서비스 정의 에러 (SequenceStoreUnavailableError, MLEndpointUnavailableError 등)
    # request_id는 endpoint 내부에서 생성되므로 exception handler 단계에선 null이다.
    logger.error("AppError [%s]: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.code, message=exc.message).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # 예상하지 못한 예외: 내부 오류가 클라이언트에 노출되지 않도록 generic 메시지를 반환한다.
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ).model_dump(),
    )


# ============================================================
# Endpoints
# ============================================================

@app.get("/health", response_model=HealthResponse)
def health():
    # liveness probe: 프로세스가 살아있는지만 확인. 의존성 상태는 /ready에서 확인.
    return HealthResponse(status="ok")


@app.get("/ready", response_model=ReadyResponse)
def ready():
    # readiness probe: DynamoDB와 SageMaker 접근 가능 여부를 각각 확인한다.
    # [변경] model_loaded 단일 플래그 → dependencies dict로 의존성별 상태를 상세 보고.
    dynamodb_ok = store.check_connection()
    sagemaker_ok = sagemaker_client.check_connection()

    dependencies = {
        "dynamodb": dynamodb_ok,
        "sagemaker_runtime": sagemaker_ok,
    }

    if not all(dependencies.values()):
        # 의존성 중 하나라도 접근 불가면 503으로 준비 안 됨을 알린다.
        return JSONResponse(
            status_code=503,
            content=ReadyResponse(
                status="not ready",
                dependencies=dependencies,
            ).model_dump(),
        )

    return ReadyResponse(status="ready", dependencies=dependencies)


@app.post("/recommend", response_model=RecommendResponse)
def recommend(body: RecommendRequest):
    # request_id: 이 요청의 전체 추적 ID. 로그와 SageMaker payload에서 일관되게 사용한다.
    request_id = f"req-{uuid.uuid4().hex[:12]}"

    # [변경] candidate_items 파라미터 제거.
    # 서비스가 DynamoDB에서 조회하고, SageMaker scoring 후 fallback까지 처리한다.
    items, fallback_used = recommend_service.recommend(
        request_id=request_id,
        user_id=body.user_id,
        top_k=body.top_k,
    )

    return RecommendResponse(
        items=items,
        request_id=request_id,
        model_version=MODEL_VERSION,
        fallback_used=fallback_used,
    )
