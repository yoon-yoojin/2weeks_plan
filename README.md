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

```text
+---------------------+
| Open Log Dataset    |
| (e.g. YOOCHOOSE)    |
+---------------------+
          |
          v
+---------------------+
| Preprocessing Job   |
| - filter sessions   |
| - remap item ids    |
| - make sequences    |
+---------------------+
          |
          v
+---------------------+
| S3 Train/Val/Test   |
+---------------------+
          |
          v
+---------------------+
| SageMaker Training  |
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
| Endpoint Update           |
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
- `Batch pipeline`
  - 원시 로그 전처리
  - 학습 데이터 생성
  - 모델 학습 및 평가
  - 새 endpoint config 생성과 endpoint refresh 담당

## 구현 목표

- `FastAPI`로 서비스 API 구현
- 공개 로그 데이터에서 `gSASRec` 입력 생성
- `SageMaker Training Job`으로 모델 학습 및 artifact 생성
- `SageMaker Real-time Endpoint`로 실시간 scoring API 배포
- endpoint refresh, warm-up, gradual rollout, cutover/rollback 절차 구현
- autoscaling 설정과 scale-out/scale-in 동작 확인
- endpoint 단독 부하 테스트
- `FastAPI -> SageMaker endpoint` E2E 부하 테스트

## 디렉토리 구조

```text
4weeks_plan/
├── README.md
├── recsys_2week_curriculum.md
├── day1/
│   └── day1_submit.md
└── mini-recsys-serving/
    ├── README.md
    ├── app/
    │   ├── main.py
    │   ├── recommender.py
    │   ├── schemas.py
    │   └── errors.py
    ├── lambda/
    │   ├── lambda_function.py
    │   └── lambda-trust-policy.json
    ├── Dockerfile
    └── requirements.txt
```

## 현재 상태

- `mini-recsys-serving/app`의 현재 FastAPI는 아직 완전한 서비스 API가 아니라, 로컬 scorer를 직접 호출하는 단순 scoring API에 가깝습니다.
- 최종 목표는 이를 `서비스 API`로 리팩터링하고, 내부에서 `SageMaker endpoint`를 호출하도록 바꾸는 것입니다.

## 다음 수정 방향

- `Day 6~12` 커리큘럼을 아래 순서로 재편
  - 데이터 전처리 배치 파이프라인
  - SageMaker 학습
  - SageMaker endpoint 배포
  - endpoint refresh / warm-up / gradual rollout / cutover
  - autoscaling
  - endpoint load test
  - FastAPI와 SageMaker endpoint E2E 연동
