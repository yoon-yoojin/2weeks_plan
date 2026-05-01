import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.recommender import recommender, MODEL_VERSION
from app.schemas import (
    ErrorResponse,
    HealthResponse,
    ReadyResponse,
    RecommendRequest,
    RecommendResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    recommender.load()
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
    logger.error("AppError [%s]: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.code, message=exc.message).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ).model_dump(),
    )


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.get("/ready", response_model=ReadyResponse)
def ready():
    if not recommender.is_ready:
        return JSONResponse(
            status_code=503,
            content=ReadyResponse(status="not ready", model_loaded=False).model_dump(),
        )
    return ReadyResponse(status="ready", model_loaded=True)


@app.post("/recommend", response_model=RecommendResponse)
def recommend(body: RecommendRequest):
    from app.errors import ModelNotReadyError
    if not recommender.is_ready:
        raise ModelNotReadyError()

    request_id = f"req-{uuid.uuid4().hex[:12]}"
    items = recommender.score(body.user_id, body.candidate_items, body.top_k)

    return RecommendResponse(
        items=items,
        request_id=request_id,
        model_version=MODEL_VERSION,
    )
