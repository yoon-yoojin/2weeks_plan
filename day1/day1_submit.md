# POST /recommend API Spec

사용자와 후보 상품 목록을 받아 점수화/정렬된 추천 결과를 반환하는 ML ranking API다.
후보 생성과 fallback은 업스트림 추천 API의 책임이며, 이 API는 후보 scoring/ranking만 수행한다.

---

## 1. 기본 정보

| 항목 | 값 |
| --- | --- |
| Method | `POST` |
| URL | `/recommend` |
| Content-Type | `application/json` |
| Accept | `application/json` |

---

## 2. Request

### Request Body

| 필드 | 타입 | 필수 여부 | 설명 | 예시 |
| --- | --- | --- | --- | --- |
| `user_id` | string | Y | 추천 대상 사용자 ID | `"u123"` |
| `candidate_items` | array[string] | Y | 업스트림에서 생성한 후보 상품 ID 목록 | `["g101", "g205", "g330"]` |
| `top_k` | integer | N | 반환할 추천 상품 개수 | `20` |
| `device` | string | N | 요청이 발생한 디바이스 | `"app"` |

### Request Validation Rules

| 필드 | 검증 규칙 |
| --- | --- |
| `user_id` | 필수, string, 빈 문자열 불가 |
| `candidate_items` | 필수, array[string], 최소 1개 이상 |
| `top_k` | 선택, integer, 기본값 `20`, 허용 범위 `1` ~ `100` |
| `device` | 선택, string, 허용값 `web`, `app`, `mobile`, 미입력 시 기본값 `web` |

### Request Example

```json
{
  "user_id": "u123",
  "candidate_items": ["g101", "g205", "g330", "g412", "g588"],
  "top_k": 20,
  "device": "app"
}
```

---

## 3. Response

### Response Body

| 필드 | 타입 | 설명 | 예시 |
| --- | --- | --- | --- |
| `items` | array[object] | 추천 결과 목록. `score` 기준 내림차순 정렬 | `[{"item_id":"g101","score":0.982},{"item_id":"g205","score":0.941}]` |
| `request_id` | string | 요청 추적용 ID | `"req-20260430-abc123"` |
| `model_version` | string | 사용된 추천 모델 버전 | `"recommend-v1.0.0"` |

### Item Object

| 필드 | 타입 | 설명 | 예시 |
| --- | --- | --- | --- |
| `item_id` | string | 추천 상품 ID | `"g101"` |
| `score` | number | 추천 점수 | `0.982` |

### Response Example

```json
{
  "items": [
    { "item_id": "g101", "score": 0.982 },
    { "item_id": "g205", "score": 0.941 },
    { "item_id": "g330", "score": 0.887 }
  ],
  "request_id": "req-20260430-abc123",
  "model_version": "recommend-v1.0.0"
}
```

---

## 4. Health Check

| 엔드포인트 | Method | 설명 |
| --- | --- | --- |
| `/health` | `GET` | 서버 liveness 확인 |
| `/ready` | `GET` | 모델 로딩 여부 확인 (readiness) |

### `/health` Response Example

```json
{ "status": "ok" }
```

### `/ready` Response Example

```json
{ "status": "ready", "model_loaded": true }
```

`model_loaded`가 `false`이면 `503`을 반환한다.

---

## 5. Status Code

| Status Code | 의미 | 설명 |
| --- | --- | --- |
| `200 OK` | 성공 | 추천 결과를 정상적으로 반환함 |
| `400 Bad Request` | 잘못된 요청 | 스키마는 유효하나 서비스 정책상 처리 불가한 요청 |
| `422 Unprocessable Entity` | 요청 검증 실패 | 필수 필드 누락, 잘못된 타입, 허용 범위/허용값 위반 |
| `500 Internal Server Error` | 서버 오류 | 예상하지 못한 서버 내부 오류 |
| `503 Service Unavailable` | 서비스 사용 불가 | 모델이 로딩되지 않았거나 의존 리소스 사용 불가 |

---

## 6. Error Response

### Error Response Body

| 필드 | 타입 | 설명 | 예시 |
| --- | --- | --- | --- |
| `code` | string | 에러 코드 | `"VALIDATION_ERROR"` |
| `message` | string | 클라이언트에 안전한 에러 메시지 | `"candidate_items must not be empty"` |
| `request_id` | string | 요청 추적용 ID | `"req-20260430-abc123"` |

### Error Policy

| 상황 | Status Code | Error Code | 설명 |
| --- | --- | --- | --- |
| 필드 타입 오류, 필수값 누락, 범위/enum 위반 | `422` | `VALIDATION_ERROR` | Pydantic 검증 실패 전체 |
| 서비스 정책상 처리 불가한 요청 | `400` | `BAD_REQUEST` | 지원하지 않는 요청 조합, 비즈니스 룰 위반 |
| 모델 미준비 또는 의존 리소스 장애 | `503` | `MODEL_UNAVAILABLE` | `/ready` 가 false인 상태에서 추천 요청이 들어온 경우 포함 |
| 예상하지 못한 서버 내부 예외 | `500` | `INTERNAL_ERROR` | 상세 원인은 서버 로그에만 기록 |

### Error Response Example

```json
{
  "code": "VALIDATION_ERROR",
  "message": "candidate_items must not be empty",
  "request_id": "req-20260430-abc123"
}
```

---

## 7. Test Cases

| 테스트 케이스 | 요청 예시 | 기대 결과 |
| --- | --- | --- |
| 정상 요청 | `user_id="u123", candidate_items=["g101","g205"], top_k=20, device="app"` | `200 OK`, 추천 결과 반환 |
| `user_id` 누락 | `candidate_items=["g101"], top_k=20` | `422`, `VALIDATION_ERROR` |
| `candidate_items` 누락 | `user_id="u123", top_k=20` | `422`, `VALIDATION_ERROR` |
| `candidate_items` 빈 배열 | `user_id="u123", candidate_items=[]` | `422`, `VALIDATION_ERROR` |
| `candidate_items` 타입 오류 | `user_id="u123", candidate_items=[1, 2, 3]` | `422`, `VALIDATION_ERROR` |
| `top_k` 범위 위반 | `user_id="u123", candidate_items=["g101"], top_k=0` | `422`, `VALIDATION_ERROR` |
| `device` 허용값 위반 | `user_id="u123", candidate_items=["g101"], device="tv"` | `422`, `VALIDATION_ERROR` |
| 모델 미준비 상태 | 정상 요청이지만 모델 미로딩 | `503`, `MODEL_UNAVAILABLE` |
| 서버 내부 예외 | 정상 요청이지만 처리 중 예외 발생 | `500`, `INTERNAL_ERROR` |

---

## 8. 설명

이 API는 업스트림 추천 API로부터 사용자 ID와 후보 상품 목록을 받아 각 후보에 점수를 매기고 상위 `top_k`개를 반환한다.

후보 생성, fallback(인기 상품 대체 등)은 업스트림 책임이며 이 API는 수행하지 않는다.

`request_id`는 로그 추적과 장애 분석을 위해 사용한다.

`model_version`은 어떤 추천 모델 버전으로 응답이 생성되었는지 확인하기 위해 사용한다.

에러 응답의 `message`는 클라이언트에 안전한 내용만 담으며, 상세 원인은 서버 로그에만 기록한다.
