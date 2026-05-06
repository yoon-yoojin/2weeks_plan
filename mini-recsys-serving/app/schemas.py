from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# Client → FastAPI
# ============================================================

class Device(str, Enum):
    web = "web"
    app = "app"
    mobile = "mobile"


class RecommendRequest(BaseModel):
    # [변경] candidate_items 제거: 클라이언트는 user_id만 보냄.
    # sequence와 candidates는 서비스가 DynamoDB에서 직접 조회한다.
    user_id: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)  # [변경] 기본값 20 → 10 (contract 기준)
    device: Device = Field(default=Device.web)


class ItemScore(BaseModel):
    # 최종 응답용 item_id는 string으로 변환해서 반환 (내부 계산은 int)
    item_id: str
    score: float


class RecommendResponse(BaseModel):
    items: List[ItemScore]
    request_id: str
    model_version: str
    # [추가] fallback 발생 시 그 사유를 기록. 정상이면 null.
    # 가능한 값: "cold_start_user" | "missing_candidates" | "endpoint_timeout" | "endpoint_error"
    fallback_used: Optional[str] = None


# ============================================================
# FastAPI → SageMaker (내부 계약 — 클라이언트에 노출되지 않음)
# ============================================================

class SageMakerRequest(BaseModel):
    # FastAPI가 SageMaker endpoint로 보내는 payload
    request_id: str
    user_id: str
    sequence: List[int]           # DynamoDB에서 조회한 유저 행동 시퀀스
    candidate_item_ids: List[int] # DynamoDB에서 조회한 후보군
    top_k: int


class SageMakerRankedItem(BaseModel):
    item_id: int  # SageMaker 내부에서는 int, 최종 응답 직전에 string으로 변환
    score: float


class SageMakerResponse(BaseModel):
    # SageMaker endpoint가 반환하는 응답 구조
    request_id: str
    model_version: str
    ranked_items: List[SageMakerRankedItem]


# ============================================================
# Health / Ready
# ============================================================

class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    # [변경] model_loaded: bool → dependencies: dict
    # 서비스 API는 로컬 모델이 없으므로 의존성(DynamoDB, SageMaker) 상태를 보고한다.
    dependencies: Dict[str, bool]


# ============================================================
# Error
# ============================================================

class ErrorResponse(BaseModel):
    code: str
    message: str
    # request_id가 있으면 포함. exception handler 단계에선 아직 없을 수 있으므로 Optional.
    request_id: Optional[str] = None
