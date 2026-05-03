# mini-recsys-serving

FastAPI 기반 ML ranking API. 업스트림 추천 API로부터 사용자 ID와 후보 상품 목록을 받아 점수화/정렬된 추천 결과를 반환한다.

후보 생성과 fallback은 업스트림 책임이며, 이 서버는 scoring/ranking만 수행한다.

## API 명세

전체 명세: [`../day1/day1_submit.md`](../day1/day1_submit.md)

| 엔드포인트 | 설명 |
|---|---|
| `POST /recommend` | 후보 상품 scoring/ranking |
| `GET /health` | 서버 liveness 확인 |
| `GET /ready` | 모델 로딩 여부 확인 |

## 구조

```
app/
├── main.py          # FastAPI 앱, exception handler, 엔드포인트
├── schemas.py       # Pydantic request/response 모델
├── recommender.py   # scoring 로직 (현재 더미)
└── errors.py        # 커스텀 에러 클래스
lambda/
├── lambda_function.py       # AWS Lambda 핸들러
└── lambda-trust-policy.json # Lambda 실행 Role IAM trust policy
```

## Lambda 핸즈온 (Day 5)

AWS Lambda + API Gateway를 직접 연결해 서버리스 API 호출 흐름을 실습했다.

- AWS 공식 Python handler 예제 기반으로 `lambda_function.py` 작성
- API Gateway HTTP API를 Lambda에 연결해 HTTPS 엔드포인트 생성
- API Gateway proxy integration 특성상 요청 body가 `event['body']`에 JSON 문자열로 전달됨을 확인
- CloudWatch Logs에서 invocation 로그 확인

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs

## Docker 실행

```bash
# 이미지 빌드
docker build -t mini-recsys-api .

# 컨테이너 실행 (포그라운드, 로그 바로 확인 가능)
docker run -p 8000:8000 mini-recsys-api

# 백그라운드 실행
docker run -d -p 8000:8000 mini-recsys-api
docker logs -f <컨테이너ID>   # 실시간 로그 확인
```

`-p 8000:8000`은 `호스트포트:컨테이너포트` 매핑. 컨테이너 내부 uvicorn은 `0.0.0.0:8000`으로 바인딩되어 외부 접근을 허용한다.

## ECR 푸시

```bash
# ECR 로그인 (12시간 유효)
aws ecr get-login-password --region ap-northeast-2 \
  | docker login --username AWS --password-stdin \
  767398048885.dkr.ecr.ap-northeast-2.amazonaws.com

# 로컬 이미지에 ECR URI 태그 붙이기
docker tag mini-recsys-api:latest \
  767398048885.dkr.ecr.ap-northeast-2.amazonaws.com/mini-recsys-api:latest

# ECR에 푸시
docker push \
  767398048885.dkr.ecr.ap-northeast-2.amazonaws.com/mini-recsys-api:latest

# 푸시 확인
aws ecr describe-images \
  --repository-name mini-recsys-api \
  --region ap-northeast-2
```

ECR 레포지토리: `767398048885.dkr.ecr.ap-northeast-2.amazonaws.com/mini-recsys-api`

## 에러 코드

| Status | Code | 설명 |
|---|---|---|
| 422 | `VALIDATION_ERROR` | 필드 타입 오류, 필수값 누락, 범위/enum 위반 |
| 400 | `BAD_REQUEST` | 서비스 정책상 처리 불가한 요청 |
| 503 | `MODEL_UNAVAILABLE` | 모델 미준비 또는 의존 리소스 장애 |
| 500 | `INTERNAL_ERROR` | 예상하지 못한 서버 내부 오류 |
