from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class Device(str, Enum):
    web = "web"
    app = "app"
    mobile = "mobile"


class RecommendRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    candidate_items: List[str] = Field(..., min_length=1)
    top_k: int = Field(default=20, ge=1, le=100)
    device: Device = Field(default=Device.web)

    @field_validator("candidate_items")
    @classmethod
    def items_must_be_non_empty_strings(cls, v: List[str]) -> List[str]:
        for item in v:
            if not item.strip():
                raise ValueError("candidate_items must not contain empty strings")
        return v


class ItemScore(BaseModel):
    item_id: str
    score: float


class RecommendResponse(BaseModel):
    items: List[ItemScore]
    request_id: str
    model_version: str


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    model_loaded: bool


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: Optional[str] = None
