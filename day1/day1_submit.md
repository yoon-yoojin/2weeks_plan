# POST /recommend API Spec

사용자와 요청 컨텍스트를 기반으로 추천 상품 목록을 반환하는 API다.

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
| `query` | string | N | 검색어 또는 추천 컨텍스트 | `"니트"` |
| `top_k` | integer | N | 반환할 추천 상품 개수 | `20` |
| `device` | string | N | 요청이 발생한 디바이스 | `"app"` |

### Request Validation Rules

| 필드 | 검증 규칙 |
| --- | --- |
| `user_id` | 필수, string, 빈 문자열 불가 |
| `query` | 선택, string, 미입력 또는 빈 문자열이면 일반 추천 컨텍스트로 처리 |
| `top_k` | 선택, integer, 기본값 `20`, 허용 범위 `1` ~ `100` |
| `device` | 선택, string, 허용값 `web`, `app`, `mobile`, 미입력 시 기본값 `web` |

### Request Example

```json
{
  "user_id": "u123",
  "query": "니트",
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
| `fallback_used` | boolean | fallback 로직 사용 여부 | `false` |
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
  "fallback_used": false,
  "request_id": "req-20260430-abc123",
  "model_version": "recommend-v1.0.0"
}
```

---

## 4. Status Code

| Status Code | 의미 | 설명 |
| --- | --- | --- |
| `200 OK` | 성공 | 추천 결과를 정상적으로 반환함 |
| `422 Unprocessable Entity` | 요청 검증 실패 | 필수 필드 누락, 잘못된 타입, 허용 범위/허용값 위반 |
| `500 Internal Server Error` | 서버 오류 | 서버 내부 처리 중 오류 발생 |
| `503 Service Unavailable` | 서비스 사용 불가 | 추천 모델 또는 의존 서비스 사용 불가 |

---

## 5. Error Response

### Error Response Body

| 필드 | 타입 | 설명 | 예시 |
| --- | --- | --- | --- |
| `code` | string | 에러 코드 | `"INVALID_REQUEST"` |
| `message` | string | 에러 메시지 | `"top_k must be greater than 0"` |
| `request_id` | string | 요청 추적용 ID | `"req-20260430-abc123"` |

### Error Policy

| 상황 | Status Code | Error Code | 설명 |
| --- | --- | --- | --- |
| `user_id` 누락 | `422` | `INVALID_USER_ID` | 필수 필드가 없거나 빈 문자열인 경우 |
| `top_k` 범위 위반 | `422` | `INVALID_TOP_K` | `top_k`가 `1` 미만 또는 `100` 초과인 경우 |
| `device` 허용값 위반 | `422` | `INVALID_DEVICE` | `web`, `app`, `mobile` 이외의 값이 들어온 경우 |
| 모델/의존 서비스 장애 | `503` | `MODEL_UNAVAILABLE` | 추천 모델 또는 외부 의존 서비스 호출 실패 |
| 서버 내부 예외 | `500` | `INTERNAL_ERROR` | 예상하지 못한 애플리케이션 오류 |

### Error Response Example

```json
{
  "code": "INVALID_TOP_K",
  "message": "top_k must be greater than 0",
  "request_id": "req-20260430-abc123"
}
```

---

## 6. Test Cases

| 테스트 케이스 | 요청 예시 | 기대 결과 |
| --- | --- | --- |
| 정상 요청 | `user_id="u123", query="니트", top_k=20, device="app"` | `200 OK`, 추천 결과 반환, `fallback_used=false` |
| fallback 응답 | `user_id="new_user_1", query="", top_k=10, device="web"` | `200 OK`, 추천 결과 반환, `fallback_used=true` |
| 필수 필드 누락 | `query="니트", top_k=20, device="app"` | `422`, `INVALID_USER_ID` |
| `top_k` 범위 위반 | `user_id="u123", top_k=0` | `422`, `INVALID_TOP_K` |
| `device` 허용값 위반 | `user_id="u123", device="tv"` | `422`, `INVALID_DEVICE` |
| 모델 장애 | 정상 요청이지만 모델 서버 실패 | `503`, `MODEL_UNAVAILABLE` |

---

## 7. 설명

이 API는 클라이언트가 사용자 ID, 검색어 또는 추천 컨텍스트, 반환 개수, 디바이스 정보를 전달하면 추천 상품 목록과 각 상품의 점수를 반환한다.

`fallback_used`는 개인화 추천 결과를 만들 수 없어서 인기 상품, 기본 추천, 룰 기반 추천 등 대체 로직을 사용했는지 여부를 나타낸다.

`request_id`는 로그 추적과 장애 분석을 위해 사용한다.

`model_version`은 어떤 추천 모델 버전으로 응답이 생성되었는지 확인하기 위해 사용한다.
