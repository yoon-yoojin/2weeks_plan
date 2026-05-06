"""추천 서비스 오케스트레이션 레이어.

[변경] Recommender(로컬 더미 scoring) → RecommendService(DynamoDB + SageMaker 오케스트레이터)

흐름:
  1. DynamoDB에서 user sequence 조회
  2. DynamoDB에서 candidate set 조회
  3. candidate cutoff 적용 (최대 200개)
  4. SageMaker endpoint로 scoring 요청
  5. 각 단계 실패 시 fallback 반환
"""
import logging
from typing import List, Optional, Tuple

from app.schemas import ItemScore, SageMakerRequest, SageMakerResponse, SageMakerRankedItem
from app.store import store
from app.sagemaker_client import sagemaker_client, EndpointTimeoutError, EndpointInvokeError

logger = logging.getLogger(__name__)

# SageMaker endpoint에 한 번에 전달하는 최대 후보 수.
# 후보군이 이보다 크면 앞에서부터 잘라낸다 (upstream에서 우선순위 정렬 가정).
CANDIDATE_CUTOFF = 200

# SageMaker endpoint에 적재된 모델 버전 식별자.
# 실제 운영에서는 endpoint describe 응답이나 환경 변수로 주입한다.
MODEL_VERSION = "gsasrec-v1"

# ────────────────────────────────────────────────────
# Fallback: 1차 구현에서는 하드코딩된 인기 상품 목록을 사용한다.
# 추후 DynamoDB popular_items 테이블이나 별도 설정 파일로 교체 가능.
# ────────────────────────────────────────────────────
_FALLBACK_ITEMS: List[SageMakerRankedItem] = [
    SageMakerRankedItem(item_id=1001, score=0.99),
    SageMakerRankedItem(item_id=1002, score=0.98),
    SageMakerRankedItem(item_id=1003, score=0.97),
    SageMakerRankedItem(item_id=1004, score=0.96),
    SageMakerRankedItem(item_id=1005, score=0.95),
    SageMakerRankedItem(item_id=1006, score=0.94),
    SageMakerRankedItem(item_id=1007, score=0.93),
    SageMakerRankedItem(item_id=1008, score=0.92),
    SageMakerRankedItem(item_id=1009, score=0.91),
    SageMakerRankedItem(item_id=1010, score=0.90),
]


def _to_item_scores(ranked: List[SageMakerRankedItem], top_k: int) -> List[ItemScore]:
    # SageMakerRankedItem(item_id: int) → ItemScore(item_id: str) 변환 + top_k 적용
    return [
        ItemScore(item_id=str(r.item_id), score=r.score)
        for r in ranked[:top_k]
    ]


class RecommendService:
    def recommend(
        self,
        request_id: str,
        user_id: str,
        top_k: int,
    ) -> Tuple[List[ItemScore], Optional[str]]:
        """추천 파이프라인을 오케스트레이션한다.

        반환: (items, fallback_used)
          - items: 최종 추천 결과
          - fallback_used: 정상이면 None, fallback 발생 시 그 사유 문자열
        """

        # ── Step 1: user sequence 조회 ──────────────────────────────
        # 시퀀스가 없으면 신규/비활성 유저로 판단해 cold start fallback을 사용한다.
        sequence = store.get_sequence(user_id)
        if not sequence:
            logger.info("[%s] cold_start_user: no sequence for user=%s", request_id, user_id)
            return _to_item_scores(_FALLBACK_ITEMS, top_k), "cold_start_user"

        # ── Step 2: candidate set 조회 ──────────────────────────────
        # 후보군이 없으면 upstream이 아직 생성하지 못한 것으로 판단한다.
        candidate_item_ids = store.get_candidates(user_id)
        if not candidate_item_ids:
            logger.info("[%s] missing_candidates: no candidates for user=%s", request_id, user_id)
            return _to_item_scores(_FALLBACK_ITEMS, top_k), "missing_candidates"

        # ── Step 3: candidate cutoff ────────────────────────────────
        # endpoint 부하 제어를 위해 최대 CANDIDATE_CUTOFF개까지만 전달한다.
        if len(candidate_item_ids) > CANDIDATE_CUTOFF:
            candidate_item_ids = candidate_item_ids[:CANDIDATE_CUTOFF]

        # ── Step 4: SageMaker endpoint scoring ─────────────────────
        sm_request = SageMakerRequest(
            request_id=request_id,
            user_id=user_id,
            sequence=sequence,
            candidate_item_ids=candidate_item_ids,
            top_k=top_k,
        )

        try:
            sm_response: SageMakerResponse = sagemaker_client.score(sm_request)
        except EndpointTimeoutError:
            # endpoint가 응답 시간 초과 → fallback
            logger.warning("[%s] endpoint_timeout fallback", request_id)
            return _to_item_scores(_FALLBACK_ITEMS, top_k), "endpoint_timeout"
        except EndpointInvokeError:
            # endpoint 5xx 또는 invoke 오류 → fallback
            logger.error("[%s] endpoint_error fallback", request_id)
            return _to_item_scores(_FALLBACK_ITEMS, top_k), "endpoint_error"

        # ── Step 5: 응답 변환 ───────────────────────────────────────
        # SageMaker 응답은 이미 top_k 기준으로 정렬되어 있다고 가정한다.
        items = _to_item_scores(sm_response.ranked_items, top_k)
        return items, None


# 모듈 수준 싱글턴
recommend_service = RecommendService()
