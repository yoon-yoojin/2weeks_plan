import random
from typing import List
from app.schemas import ItemScore


MODEL_VERSION = "recommend-v1.0.0"


class Recommender:
    def __init__(self):
        self._model_loaded = False

    def load(self):
        # 실제 모델 로딩 자리. 현재는 플래그만 세팅.
        self._model_loaded = True

    @property
    def is_ready(self) -> bool:
        return self._model_loaded

    def score(self, user_id: str, candidate_items: List[str], top_k: int) -> List[ItemScore]:
        scores = [
            ItemScore(item_id=item_id, score=round(random.uniform(0.5, 1.0), 3))
            for item_id in candidate_items
        ]
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores[:top_k]


recommender = Recommender()
