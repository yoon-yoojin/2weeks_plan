# mini-recsys-serving

FastAPI 기반 서비스 API. 클라이언트로부터 `user_id`를 받아 DynamoDB에서 유저 시퀀스와 후보군을 조회하고, SageMaker real-time endpoint로 scoring한 뒤 추천 결과를 반환한다.

## API 명세

| 엔드포인트 | 설명 |
|---|---|
| `POST /recommend` | 추천 결과 반환 |
| `GET /health` | 서버 liveness 확인 |
| `GET /ready` | 의존성(DynamoDB, SageMaker) 준비 상태 확인 |

전체 계약: [`contract.md`](./contract.md)

## 구조

```
app/
├── main.py              # FastAPI 앱, exception handler, 엔드포인트
├── schemas.py           # Pydantic request/response 모델 (client / SageMaker 내부 계약 분리)
├── recommender.py       # 서비스 오케스트레이터 (DynamoDB 조회 → SageMaker scoring → fallback)
├── store.py             # DynamoDB 조회 레이어
├── sagemaker_client.py  # SageMaker endpoint 호출 레이어
└── errors.py            # 커스텀 에러 클래스
lambda/
├── lambda_function.py       # AWS Lambda 핸들러
└── lambda-trust-policy.json # Lambda 실행 Role IAM trust policy
```

## ⚠️ 실행 전 필수: 환경 변수 주입

이 서비스는 DynamoDB와 SageMaker에 의존한다. **실행 전 반드시 아래 환경 변수를 설정해야 한다.**

| 환경 변수 | 설명 | 예시 |
|---|---|---|
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` |
| `DYNAMODB_USER_SEQUENCES_TABLE` | user sequence 테이블명 | `user_sequences` |
| `DYNAMODB_CANDIDATE_SETS_TABLE` | candidate set 테이블명 | `candidate_sets` |
| `SAGEMAKER_ENDPOINT_NAME` | SageMaker endpoint 이름 | `recsys-endpoint` |

## 로컬 실행

```bash
pip install -r requirements.txt

export AWS_REGION=ap-northeast-2
export DYNAMODB_USER_SEQUENCES_TABLE=user_sequences
export DYNAMODB_CANDIDATE_SETS_TABLE=candidate_sets
export SAGEMAKER_ENDPOINT_NAME=recsys-endpoint

uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs

## Docker 실행

```bash
# 이미지 빌드
docker build -t mini-recsys-api .

# 환경 변수를 -e 플래그로 주입해서 실행
docker run -p 8000:8000 \
  -e AWS_REGION=ap-northeast-2 \
  -e DYNAMODB_USER_SEQUENCES_TABLE=user_sequences \
  -e DYNAMODB_CANDIDATE_SETS_TABLE=candidate_sets \
  -e SAGEMAKER_ENDPOINT_NAME=recsys-endpoint \
  mini-recsys-api

# 백그라운드 실행
docker run -d -p 8000:8000 \
  -e AWS_REGION=ap-northeast-2 \
  -e DYNAMODB_USER_SEQUENCES_TABLE=user_sequences \
  -e DYNAMODB_CANDIDATE_SETS_TABLE=candidate_sets \
  -e SAGEMAKER_ENDPOINT_NAME=recsys-endpoint \
  mini-recsys-api
docker logs -f <컨테이너ID>
```

`-p 8000:8000`은 `호스트포트:컨테이너포트` 매핑. 컨테이너 내부 uvicorn은 `0.0.0.0:8000`으로 바인딩되어 외부 접근을 허용한다.

## ECR 푸시

```bash
# ECR 로그인 (12시간 유효)
aws ecr get-login-password --region ap-northeast-2 \
  | docker login --username AWS --password-stdin \
  <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com

# 로컬 이미지에 ECR URI 태그 붙이기
docker tag mini-recsys-api:latest \
  <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/mini-recsys-api:latest

# ECR에 푸시
docker push \
  <AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/mini-recsys-api:latest

# 푸시 확인
aws ecr describe-images \
  --repository-name mini-recsys-api \
  --region ap-northeast-2
```

ECR 레포지토리: `<AWS_ACCOUNT_ID>.dkr.ecr.ap-northeast-2.amazonaws.com/mini-recsys-api`

## Lambda 핸즈온 (Day 5)

AWS Lambda + API Gateway를 직접 연결해 서버리스 API 호출 흐름을 실습했다.

- AWS 공식 Python handler 예제 기반으로 `lambda_function.py` 작성
- API Gateway HTTP API를 Lambda에 연결해 HTTPS 엔드포인트 생성
- API Gateway proxy integration 특성상 요청 body가 `event['body']`에 JSON 문자열로 전달됨을 확인
- CloudWatch Logs에서 invocation 로그 확인

## 에러 코드

| Status | Code | 설명 |
|---|---|---|
| `422` | `VALIDATION_ERROR` | 필드 타입 오류, 필수값 누락, 범위/enum 위반 |
| `400` | `BAD_REQUEST` | 서비스 정책상 처리 불가한 요청 |
| `503` | `SEQUENCE_STORE_UNAVAILABLE` | DynamoDB 접근 불가 |
| `503` | `ML_ENDPOINT_UNAVAILABLE` | SageMaker endpoint invoke 실패 |
| `500` | `INTERNAL_ERROR` | 예상하지 못한 서버 내부 오류 |
