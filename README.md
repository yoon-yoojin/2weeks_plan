# RecSys Serving Engineering

추천 모델을 직접 서빙하는 운영 환경을 최대한 비슷하게 재현하는 실습 저장소입니다. 핵심 목표는 `FastAPI 서비스 API`와 `SageMaker ML endpoint`를 분리하고, 데이터 전처리부터 학습, 배포, 리프레시, 스케일링, 부하 테스트, E2E 호출까지 한 흐름으로 구현하는 것입니다.

## 목표 아키텍처

```text
+-------------------+
| Client / Tester   |
+-------------------+
          |
          v
+-------------------+
| FastAPI Service   |
| - validate req    |
| - request_id      |
| - context lookup  |
| - candidate build |
| - timeout/retry   |
| - fallback        |
+-------------------+
          |
          v
+-----------------------------+
| SageMaker Runtime Invoke    |
+-----------------------------+
          |
          v
+-----------------------------+
| SageMaker Real-time EP      |
| - gSASRec inference         |
| - input_fn                  |
| - predict_fn                |
| - output_fn                 |
+-----------------------------+
          |
          v
+-------------------+
| Ranked Scores     |
+-------------------+
          |
          v
+-------------------+
| FastAPI Response  |
+-------------------+
```

## 배치 파이프라인

전처리, 학습, 추론 모두 SageMaker 인프라에서 실행합니다.

```text
+---------------------+
| Open Log Dataset    |
| (e.g. YOOCHOOSE)    |
| → S3 raw prefix     |
+---------------------+
          |
          v
+------------------------------+
| SageMaker Processing Job     |
| (SKLearnProcessor)           |
| - filter sessions            |
| - remap item ids             |
| - make sequences             |
| input:  s3://.../raw/        |
| output: s3://.../input/      |
+------------------------------+
          |
          v
+---------------------+
| S3 Train/Val/Test   |
+---------------------+
          |
          v
+---------------------+
| SageMaker Training  |
| Job                 |
| - train gSASRec     |
| - eval metrics      |
+---------------------+
          |
          v
+---------------------+
| Model Artifact in S3|
+---------------------+
          |
          v
+---------------------------+
| New Model / EndpointConfig|
+---------------------------+
          |
          v
+---------------------------+
| SageMaker Endpoint Update |
| - refresh                 |
| - warm-up                 |
| - gradual rollout         |
| - cutover / rollback      |
+---------------------------+
          |
          v
+---------------------------+
| Auto Scaling Attached     |
| - scale out               |
| - scale in                |
+---------------------------+
```

## 서비스 호출 흐름

```text
+----------------------+
| Client               |
| POST /recommend      |
+----------------------+
          |
          v
+----------------------+
| FastAPI Service API  |
| - parse request      |
| - load user context  |
| - build candidates   |
+----------------------+
          |
          v
+----------------------+
| Invoke ML Endpoint   |
| sequence + candidates|
+----------------------+
          |
          v
+----------------------+
| SageMaker Endpoint   |
| returns item scores  |
+----------------------+
          |
          v
+----------------------+
| FastAPI              |
| - rerank/fallback    |
| - build response     |
+----------------------+
          |
          v
+----------------------+
| Client Response      |
+----------------------+
```

## 역할 분리

- `FastAPI`
  - 서비스 API
  - 클라이언트 요청을 직접 받음
  - 후보군 생성, 컨텍스트 조회, timeout/retry, fallback, 응답 조립 담당
- `SageMaker endpoint`
  - ML scoring API
  - 시퀀스/후보군을 입력받아 모델 점수 또는 top-k 결과 반환
- `Batch pipeline` (전처리/학습/추론 모두 SageMaker에서 실행)
  - SageMaker Processing Job으로 원시 로그 전처리 및 학습 데이터 생성
  - SageMaker Training Job으로 모델 학습 및 평가
  - 새 endpoint config 생성과 SageMaker endpoint refresh 담당

## 구현 목표

- `FastAPI`로 서비스 API 구현
- 공개 로그 데이터에서 `gSASRec` 입력 생성
- `SageMaker Training Job`으로 모델 학습 및 artifact 생성
- `SageMaker Real-time Endpoint`로 실시간 scoring API 배포
- endpoint refresh, warm-up, gradual rollout, cutover/rollback 절차 구현
- autoscaling 설정과 scale-out/scale-in 동작 확인
- endpoint 단독 부하 테스트
- `FastAPI -> SageMaker endpoint` E2E 부하 테스트

## 진행 현황

| Day | 주제 | 상태 |
|---|---|---|
| Day 1 | HTTP/REST/FastAPI 기본 + 추천 API 계약 정의 | ✅ 완료 |
| Day 2 | FastAPI 추천 API 구현 | ✅ 완료 |
| Day 3 | Docker로 FastAPI 컨테이너화 | ✅ 완료 |
| Day 4 | ECR에 이미지 푸시 | ✅ 완료 |
| Day 5 | AWS Lambda + API Gateway 실제 배포 | ✅ 완료 |
| Day 6 | 서비스 API 역할 정리 + gSASRec 배치 파이프라인 설계 | ✅ 완료 |
| Day 7 | 공개 로그 데이터 전처리 + SageMaker 학습 입력 생성 | ⬜ 미완료 |
| Day 8 | SageMaker training job으로 gSASRec 학습 | ⬜ 미완료 |
| Day 9 | 추론 스크립트 구현 + 실시간 endpoint 생성 | ⬜ 미완료 |
| Day 10 | SageMaker Pipelines로 전처리→학습→배포 파이프라인 구성 | ⬜ 미완료 |
| Day 11 | endpoint refresh, warm-up, 점진 배포, cutover | ⬜ 미완료 |
| Day 12 | autoscaling 설정 + endpoint 부하 테스트 | ⬜ 미완료 |
| Day 13 | FastAPI 서비스 API에서 SageMaker endpoint 호출 + E2E 테스트 | ⬜ 미완료 |
| Day 14 | 최종 통합: AWS 아키텍처, 운영 전략, 면접 답변 정리 | ⬜ 미완료 |

## 디렉토리 구조

```text
4weeks_plan/
├── README.md
├── recsys_2week_curriculum.md
├── day1/
│   └── day1_submit.md
└── mini-recsys-serving/
    ├── README.md
    ├── contract.md          # FastAPI ↔ SageMaker 서비스 계약 정의
    ├── app/
    │   ├── main.py              # FastAPI 앱, exception handler, 엔드포인트
    │   ├── schemas.py           # Pydantic 모델 (client / SageMaker 내부 계약 분리)
    │   ├── recommender.py       # 서비스 오케스트레이터 (DynamoDB → SageMaker → fallback)
    │   ├── store.py             # DynamoDB 조회 레이어
    │   ├── sagemaker_client.py  # SageMaker endpoint 호출 레이어
    │   └── errors.py            # 커스텀 에러 클래스
    ├── lambda/
    │   ├── lambda_function.py
    │   └── lambda-trust-policy.json
    ├── Dockerfile
    └── requirements.txt
```

## 현재 상태

- `mini-recsys-serving/app`을 ML API에서 서비스 API로 리팩토링 완료.
- 클라이언트는 `user_id`만 전달하며, 서비스가 DynamoDB에서 sequence/candidates를 조회하고 SageMaker endpoint를 호출하는 구조.
- `contract.md`에 FastAPI ↔ SageMaker 계약, DynamoDB 스키마, fallback 정책이 정의되어 있음.
- Day 7부터 실제 데이터 전처리 → SageMaker 학습 → endpoint 배포 순으로 진행 예정.

## 다음 수정 방향

- `Day 7~13` 커리큘럼을 아래 순서로 진행
  - 공개 로그 데이터(YOOCHOOSE) 전처리 + S3 업로드
  - SageMaker training job으로 gSASRec 학습
  - 추론 스크립트 구현 + real-time endpoint 배포
  - endpoint refresh / warm-up / gradual rollout / cutover / rollback
  - autoscaling 설정 + endpoint 부하 테스트
  - FastAPI → SageMaker endpoint E2E 연동 및 테스트
