# RecSys Serving Engineering

추천 모델을 직접 서빙하는 운영 환경을 최대한 비슷하게 재현하는 실습 저장소입니다. 핵심 목표는 `FastAPI 서비스 API`와 `SageMaker ML endpoint`를 분리하고, 데이터 전처리부터 학습, 배포, 리프레시, 스케일링, 부하 테스트, E2E 호출까지 한 흐름으로 구현하는 것입니다.

## 목표 아키텍처

```text
+-------------------+
| Client / Tester   |
+-------------------+
          |  user_id
          v
+---------------------------+
| FastAPI Service API       |
| - validate req            |
| - request_id 생성         |
| - DynamoDB: seq 조회      |  ← 원본 goodsno sequence
| - DynamoDB: candidates 조회| ← 원본 goodsno candidates
| - timeout/retry/fallback  |
+---------------------------+
          |  goodsno sequence + candidates
          v
+----------------------------------+
| SageMaker Real-time Endpoint     |
| - input_fn:   goodsno → int id   |  ← 순변환 (매퍼 사용)
| - predict_fn: gSASRec 추론       |
| - output_fn:  int id → goodsno   |  ← 역변환 (매퍼 사용)
+----------------------------------+
          |  ranked goodsno + scores
          v
+---------------------------+
| FastAPI Response          |
| - rerank/fallback         |
| - build response          |
+---------------------------+
          |
          v
+-------------------+
| Client Response   |
+-------------------+
```

## 배치 파이프라인

전처리, 학습, 추론 모두 SageMaker 인프라에서 실행합니다. Day 10에서 SageMaker Pipelines로 전체 흐름을 하나의 파이프라인으로 연결합니다.

```text
+---------------------+
| Open Log Dataset    |
| (e.g. YOOCHOOSE)    |
| → S3 raw prefix     |  ← 로컬에서 1회 업로드
+---------------------+
          |
          v
+------------------------------------------+
| SageMaker Processing Job (SKLearnProc)   |
| - session/item 필터링                    |
| - goodsno → integer id 매핑 생성         |
| - leave-one-out split (train/valid/test) |
| - test set 시퀀스를 DynamoDB에 적재      |  ← 원본 goodsno로 저장
| - 초기 candidate set을 DynamoDB에 적재   |  ← 원본 goodsno로 저장
|                                          |
| 산출물:                                  |
|   s3://.../gsasrec/input/train/          |  ← integer id 기반 parquet
|   s3://.../gsasrec/input/valid/          |
|   s3://.../gsasrec/input/test/           |
|   s3://.../gsasrec/meta/item2id.json     |  ← Training Job이 번들에 포함
|   s3://.../gsasrec/meta/id2item.json     |
+------------------------------------------+
          |
          v
+---------------------+
| S3 Train/Val/Test   |
+---------------------+
          |
          v
+------------------------------------------+
| SageMaker Training Job                   |
| - gSASRec 학습                           |
| - 평가 지표 기록                         |
| - model.tar.gz 생성:                     |
|     weights + item2id.json + id2item.json|  ← 매퍼와 가중치를 함께 번들
+------------------------------------------+
          |
          v
+---------------------+
| Model Artifact      |
| in S3               |
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

FastAPI는 goodsno만 알고, integer id 변환은 SageMaker endpoint 내부에서만 이루어집니다.

```text
+----------------------------------+
| Client                           |
| POST /recommend {user_id}        |
+----------------------------------+
          |
          v
+----------------------------------+
| FastAPI Service API              |
| - DynamoDB: goodsno sequence 조회|
| - DynamoDB: goodsno candidates   |
| - payload 생성                   |
+----------------------------------+
          |  {sequence: [goodsno, ...], candidates: [goodsno, ...]}
          v
+------------------------------------------+
| SageMaker Endpoint                       |
| input_fn:   goodsno → integer id 변환    |
| predict_fn: gSASRec 추론                 |
| output_fn:  integer id → goodsno 역변환  |
+------------------------------------------+
          |  {ranked_items: [{item_id: goodsno, score}, ...]}
          v
+----------------------------------+
| FastAPI                          |
| - fallback 처리                  |
| - response 조립                  |
+----------------------------------+
          |
          v
+----------------------------------+
| Client Response                  |
| {items: [{item_id: goodsno, ...}]}|
+----------------------------------+
```

## 역할 분리

- `FastAPI 서비스 API`
  - 클라이언트 요청 수신 및 응답 조립
  - DynamoDB에서 goodsno 기반 sequence / candidate 조회
  - SageMaker endpoint payload 생성 및 호출
  - timeout / retry / fallback 처리
  - **item id 변환 로직 없음 — goodsno만 다룸**

- `SageMaker ML Endpoint`
  - goodsno sequence + candidates를 입력으로 받아 ranked goodsno 반환
  - `input_fn`: goodsno → integer id 순변환 (매퍼 사용)
  - `predict_fn`: gSASRec 추론
  - `output_fn`: integer id → goodsno 역변환 (매퍼 사용)
  - **매퍼(item2id, id2item)는 model.tar.gz에 모델 가중치와 함께 번들**
  - 매퍼와 가중치는 반드시 동일 학습 실행의 산출물이어야 함 (버전 일치 필수)

- `DynamoDB`
  - `user_sequences`: user_id → goodsno sequence (원본 상품번호 기반)
  - `candidate_sets`: user_id → goodsno candidate list (원본 상품번호 기반)
  - **integer id를 저장하지 않음** — ML 내부 구조와 독립적으로 유지

- `Batch pipeline` (전처리/학습 모두 SageMaker에서 실행)
  - Processing Job: 원시 로그 전처리, 매핑 생성, DynamoDB 초기 적재
  - Training Job: gSASRec 학습, model.tar.gz(가중치 + 매퍼) 생성
  - Day 10에서 SageMaker Pipelines로 Processing → Training → Endpoint 배포를 하나의 파이프라인으로 연결
  - main 브랜치 push 시 GitHub Actions로 S3 코드 sync 및 파이프라인 정의 자동 갱신

## 아이템 ID 설계 원칙

```text
goodsno (원본 상품번호)
  - 클라이언트, FastAPI, DynamoDB에서 사용
  - ML 시스템 외부에서 공유되는 유일한 item 식별자

integer id (ML 내부 인덱스)
  - SageMaker endpoint 내부에서만 사용
  - 모델 embedding 레이어의 인덱스
  - 학습 실행마다 재생성되므로 외부에 노출하지 않음

매핑 관리 원칙
  - item2id / id2item은 Processing Job에서 생성
  - Training Job이 model.tar.gz에 가중치와 함께 번들
  - 매퍼와 가중치는 반드시 동일 학습 실행의 산출물 (버전 불일치 시 추론 결과 오염)
  - 매퍼가 바뀌어도 DynamoDB 재적재 불필요 (goodsno로 저장하기 때문)
```

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
- 클라이언트는 `user_id`만 전달하며, 서비스가 DynamoDB에서 goodsno 기반 sequence/candidates를 조회하고 SageMaker endpoint를 호출하는 구조.
- `contract.md`에 FastAPI ↔ SageMaker 계약, DynamoDB 스키마, fallback 정책이 정의되어 있음.
- 아이템 ID 설계 확정: DynamoDB는 goodsno, SageMaker endpoint 내부에서만 integer id 사용 및 역변환.
- Day 7부터 실제 데이터 전처리 → SageMaker 학습 → endpoint 배포 순으로 진행 예정.

## 다음 수정 방향

- `Day 7~14` 커리큘럼을 아래 순서로 진행
  - 공개 로그 데이터(YOOCHOOSE) 전처리 + DynamoDB 적재 + S3 업로드 (Processing Job)
  - GitHub Actions로 `sagemaker/` 코드 변경 시 S3 자동 sync
  - SageMaker Training Job으로 gSASRec 학습 (model.tar.gz에 매퍼 번들)
  - 추론 스크립트 구현: input_fn 순변환 + output_fn 역변환 + real-time endpoint 배포
  - SageMaker Pipelines로 Processing → Training → Endpoint 배포 파이프라인 구성
  - endpoint refresh / warm-up / gradual rollout / cutover / rollback
  - autoscaling 설정 + endpoint 부하 테스트
  - FastAPI → SageMaker endpoint E2E 연동 및 테스트
