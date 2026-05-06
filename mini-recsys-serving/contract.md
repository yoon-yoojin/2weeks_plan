# Service API Contract

이 문서는 `mini-recsys-serving`의 `FastAPI 서비스 API` 계약을 정의한다. 이 API는 클라이언트와 직접 통신하며, 내부적으로 `DynamoDB`에서 유저 시퀀스와 후보군을 조회하고, `SageMaker real-time endpoint`를 호출해 점수를 계산한 뒤 최종 응답을 반환한다.

이 문서의 핵심 전제는 다음과 같다.

- 클라이언트는 `candidate_items`를 직접 보내지 않는다.
- `FastAPI`는 서비스 계층이다.
- `SageMaker endpoint`는 ML scoring 계층이다.
- `user sequence`와 `candidate set`은 온라인 저장소(`DynamoDB`)에서 조회한다.
- `SageMaker endpoint` 메모리에는 모델 가중치, item mapping, 최소 metadata만 적재한다.

---

## 1. 역할 분리

### FastAPI 서비스 API
- 클라이언트 요청 수신
- request validation
- `request_id` 생성
- `user_id` 기준 유저 시퀀스 조회
- `user_id` 기준 후보군 조회
- `SageMaker endpoint`용 payload 생성
- timeout / retry / fallback 처리
- 최종 response formatting

### SageMaker ML Endpoint
- `sequence`와 `candidate_item_ids`를 입력받음
- 각 후보 item score 계산
- 정렬된 top-k 결과 또는 후보별 점수 반환

### DynamoDB
- 유저 최근 행동 시퀀스 저장
- `user_id` 기준 후보군 저장

---

## 2. 서비스 API 기본 정보

| 항목 | 값 |
| --- | --- |
| Method | `POST` |
| URL | `/recommend` |
| Content-Type | `application/json` |
| Accept | `application/json` |

---

## 3. Client -> FastAPI Request

### Request Body

| 필드 | 타입 | 필수 여부 | 설명 | 예시 |
| --- | --- | --- | --- | --- |
| `user_id` | string | Y | 추천 대상 사용자 ID | `"u123"` |
| `top_k` | integer | N | 최종 반환할 추천 개수 | `10` |
| `device` | string | N | 요청 디바이스 | `"app"` |

### Request Validation Rules

| 필드 | 검증 규칙 |
| --- | --- |
| `user_id` | 필수, string, 빈 문자열 불가 |
| `top_k` | 선택, integer, 기본값 `10`, 허용 범위 `1` ~ `100` |
| `device` | 선택, 허용값 `web`, `app`, `mobile`, 기본값 `web` |

### Request Policy

- 1차 구현에서 필수 입력은 `user_id` 하나다.
- 서비스는 `user_id`를 기준으로 `DynamoDB`에서 유저 시퀀스와 후보군을 조회한다.
- 클라이언트는 내부 모델 입력(`sequence`, `candidate_item_ids`)을 알 필요가 없다.

### Request Example

```json
{
  "user_id": "u123",
  "top_k": 10,
  "device": "app"
}
```

---

## 4. FastAPI 내부 조회 계약

이 섹션은 외부 공개 API는 아니지만, 서비스 API 구현을 위해 필요한 내부 데이터 계약을 정의한다.

### 4.1 User Sequence Store

추천 저장소 예시: `DynamoDB table = user_sequences`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `user_id` | string | partition key |
| `sequence` | array[number] | 최근 행동 item id sequence |
| `updated_at` | string | 마지막 갱신 시각 |

예시:

```json
{
  "user_id": "u123",
  "sequence": [12, 55, 91, 103],
  "updated_at": "2026-05-06T10:20:00Z"
}
```

### 4.2 Candidate Store

추천 저장소 예시: `DynamoDB table = candidate_sets`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `candidate_key` | string | 1차 구현에서는 `user#{user_id}` 형태를 사용 |
| `candidate_item_ids` | array[number] | scoring 대상 후보군 |
| `updated_at` | string | 마지막 갱신 시각 |

예시:

```json
{
  "candidate_key": "user#u123",
  "candidate_item_ids": [201, 305, 411, 502, 601],
  "updated_at": "2026-05-06T10:19:30Z"
}
```

### Internal Lookup Policy

- 유저 시퀀스가 없으면 `cold_start_user` fallback을 사용한다.
- 후보군이 없으면 `missing_candidates` fallback을 사용한다.
- 후보군이 너무 크면 서비스에서 cutoff를 적용한다.
  - 예: 상위 200개까지만 `SageMaker endpoint`에 전달

---

## 5. FastAPI -> SageMaker Request

이 요청은 내부용 계약이다. 클라이언트는 직접 호출하지 않는다.

### Request Body

| 필드 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| `request_id` | string | Y | FastAPI에서 생성한 추적 ID |
| `user_id` | string | Y | 사용자 ID |
| `sequence` | array[number] | Y | 최근 행동 시퀀스 |
| `candidate_item_ids` | array[number] | Y | 점수를 계산할 후보군 |
| `top_k` | integer | Y | 반환할 상위 결과 수 |

### Request Example

```json
{
  "request_id": "req-20260506-abc123",
  "user_id": "u123",
  "sequence": [12, 55, 91, 103],
  "candidate_item_ids": [201, 305, 411, 502, 601],
  "top_k": 10
}
```

### Request Policy

- `sequence`는 서비스 API가 `DynamoDB`에서 조회해 채운다.
- `candidate_item_ids`는 서비스 API가 `DynamoDB`에서 조회해 채운다.
- `top_k`는 최종 응답 수지만, 필요 시 endpoint는 후보 전체 점수를 계산한 뒤 top-k만 반환할 수 있다.

---

## 6. SageMaker -> FastAPI Response

### Response Body

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `request_id` | string | 요청 추적 ID |
| `model_version` | string | 사용된 모델 버전 |
| `ranked_items` | array[object] | 정렬된 추천 결과 |

### Ranked Item Object

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `item_id` | number | item id |
| `score` | number | 모델 점수 |

### Response Example

```json
{
  "request_id": "req-20260506-abc123",
  "model_version": "gsasrec-v1",
  "ranked_items": [
    { "item_id": 305, "score": 0.9123 },
    { "item_id": 201, "score": 0.8841 },
    { "item_id": 411, "score": 0.7312 }
  ]
}
```

---

## 7. FastAPI -> Client Response

### Response Body

| 필드 | 타입 | 설명 | 예시 |
| --- | --- | --- | --- |
| `items` | array[object] | 최종 추천 결과 | `[{"item_id":"305","score":0.9123}]` |
| `request_id` | string | 요청 추적 ID | `"req-20260506-abc123"` |
| `model_version` | string | 사용된 모델 버전 | `"gsasrec-v1"` |
| `fallback_used` | string or null | fallback 종류 | `"cold_start_user"` |

### Item Object

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `item_id` | string | 최종 응답용 item id |
| `score` | number | 최종 점수 |

### Response Example

```json
{
  "items": [
    { "item_id": "305", "score": 0.9123 },
    { "item_id": "201", "score": 0.8841 },
    { "item_id": "411", "score": 0.7312 }
  ],
  "request_id": "req-20260506-abc123",
  "model_version": "gsasrec-v1",
  "fallback_used": null
}
```

---

## 8. Fallback 정책

### Fallback 유형

| fallback_used | 설명 |
| --- | --- |
| `null` | 정상적으로 SageMaker endpoint scoring 수행 |
| `cold_start_user` | 유저 시퀀스가 없어 fallback 후보군 반환 |
| `missing_candidates` | 후보군 조회 실패 또는 비어 있음 |
| `endpoint_timeout` | SageMaker endpoint timeout |
| `endpoint_error` | SageMaker endpoint 5xx 또는 invoke 실패 |

### Fallback 동작 원칙

- 모든 fallback 상황에서 인기 상품 기반 기본 후보군을 반환한다.
- 1차 구현에서는 fallback 로직을 단순화하기 위해 fallback 유형과 무관하게 동일한 응답 정책을 사용한다.
- `fallback_used` 값은 어떤 이유로 fallback이 발생했는지 추적하기 위해서만 유지한다.

---

## 9. Health Check

| 엔드포인트 | Method | 설명 |
| --- | --- | --- |
| `/health` | `GET` | 프로세스 liveness 확인 |
| `/ready` | `GET` | 서비스 의존성 준비 상태 확인 |

### `/health` Response Example

```json
{ "status": "ok" }
```

### `/ready` Response Example

```json
{
  "status": "ready",
  "dependencies": {
    "dynamodb": true,
    "sagemaker_runtime": true
  }
}
```

`/ready`는 최소한 아래를 확인해야 한다.

- `DynamoDB` 접근 가능 여부
- `SageMaker runtime` invoke 가능 여부

---

## 10. Status Code

| Status Code | 의미 | 설명 |
| --- | --- | --- |
| `200 OK` | 성공 | 추천 결과 또는 fallback 결과 반환 |
| `400 Bad Request` | 잘못된 요청 | 서비스 정책 위반 |
| `422 Unprocessable Entity` | 검증 실패 | 필수 필드 누락, enum/range/type 오류 |
| `500 Internal Server Error` | 서버 오류 | 예상하지 못한 내부 예외 |
| `503 Service Unavailable` | 의존성 장애 | DynamoDB 또는 SageMaker 의존성 장애 |

---

## 11. Error Response

### Error Response Body

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `code` | string | 에러 코드 |
| `message` | string | 클라이언트에 안전한 메시지 |
| `request_id` | string | 요청 추적 ID |

### Error Code 예시

| 상황 | Status Code | Error Code |
| --- | --- | --- |
| 필수 필드 누락/타입 오류 | `422` | `VALIDATION_ERROR` |
| DynamoDB 접근 불가 | `503` | `SEQUENCE_STORE_UNAVAILABLE` |
| SageMaker endpoint invoke 실패 | `503` | `ML_ENDPOINT_UNAVAILABLE` |
| 예상하지 못한 예외 | `500` | `INTERNAL_ERROR` |

### Error Response Example

```json
{
  "code": "ML_ENDPOINT_UNAVAILABLE",
  "message": "Temporary recommendation dependency failure",
  "request_id": "req-20260506-abc123"
}
```

---

## 12. 테스트 시나리오

| 테스트 케이스 | 기대 결과 |
| --- | --- |
| 정상 요청, sequence/candidates 조회 성공, endpoint scoring 성공 | `200`, `fallback_used=null` |
| 유저 시퀀스 없음 | `200`, `fallback_used="cold_start_user"` |
| 후보군 없음 | `200`, `fallback_used="missing_candidates"` |
| SageMaker timeout | `200` 또는 `503`, 설계한 fallback 정책에 따름 |
| SageMaker 5xx | `200` fallback 또는 `503`, 설계한 정책에 따름 |
| 잘못된 request body | `422`, `VALIDATION_ERROR` |
| 의존성 장애가 readiness에 반영됨 | `/ready`에서 비정상 상태 표시 |

---

## 13. 구현 메모

- 1차 구현 기준 저장소 구성:
  - `user sequence`: `DynamoDB`
  - `candidate set`: `DynamoDB`
  - `SageMaker endpoint memory`: 모델 + item mapping + 최소 metadata
- 이 구조를 택한 이유:
  - 서비스 API와 ML endpoint 책임 분리가 명확하다.
  - endpoint refresh / warm-up / autoscaling 실습과 잘 맞는다.
  - 부하 테스트 시 병목을 `storage`, `service`, `ml endpoint`로 분리해 볼 수 있다.
