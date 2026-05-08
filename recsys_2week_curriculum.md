# 14일 집중 커리큘럼 (AWS 실계정 기반 RecSys Serving Engineering + Ops)

## 0. 목표
- 기간: 14일
- 학습 시간: 하루 4시간
- 방향:
  - 모델링은 1일로 압축
  - `FastAPI`, `Docker`, `AWS Lambda`, `API Gateway`, `ECR`, `SageMaker`를 실제 실습 중심으로 학습
  - 최종적으로 "추천 API를 로컬과 AWS에서 모두 띄우고, 배포/운영/롤백 흐름까지 설명 가능한 상태"를 만든다

## 1. 전제
- AWS 실계정이 있고, 기본적인 콘솔 접근 및 `aws cli` 사용이 가능하다고 가정한다.
- 비용 통제를 위해 실습은 작은 리소스로 진행하고, 각 Day에 `삭제` 단계를 포함한다.
- 실습 전에 최소 준비:
  - `aws configure`
  - 기본 region 확정
  - `Docker` 설치

## 2. 최종 산출물
- `mini-recsys-serving/`
  - `app/main.py`: FastAPI 추천 API
  - `app/recommender.py`: 추천 + fallback 로직
  - `app/schemas.py`: request/response schema
  - `Dockerfile`
  - `.github/workflows/ci.yml`
  - `lambda/lambda_function.py`
  - `sagemaker/inference.py`
  - `sagemaker/train_gsasrec.py`
  - `scripts/load_test_endpoint.sh`
  - `scripts/load_test_service.sh`
- `aws_runbook.md`
  - Lambda 배포/호출/삭제 절차
  - ECR push 절차
  - SageMaker endpoint 생성/검증/삭제 절차
- `design_doc_final.md`
  - API 흐름
  - AWS 아키텍처
  - 비용/운영/롤백 전략

## 3. AWS 중심 13일 상세 플랜

### Day 1. HTTP/REST/FastAPI 기본과 추천 API 계약 정의
- 학습 목표:
  - 추천 API의 입력/출력/에러 응답 구조를 정의한다.
  - 이후 AWS 실습의 기준이 되는 API contract를 만든다.
- 공부 내용:
  - HTTP method
  - status code
  - JSON request/response
  - REST API contract
- 실습:
  - `POST /recommend` 요청/응답 스펙 작성
  - 필드 예시:
    - request: `user_id`, `query`, `top_k`, `device`
    - response: `items`, `scores`, `fallback_used`, `request_id`, `model_version`
- 레퍼런스:
  - MDN HTTP Overview: [https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview)
  - FastAPI Tutorial: [https://fastapi.tiangolo.com/tutorial/](https://fastapi.tiangolo.com/tutorial/)
- 4시간 배분:
  - 1h 이론
  - 2h API schema 설계
  - 1h 테스트 케이스 정리

### Day 2. FastAPI 추천 API 구현
- 학습 목표:
  - FastAPI로 실행 가능한 추천 API를 만든다.
  - 입력 검증, health check, 기본 에러 처리를 넣는다.
- 공부 내용:
  - Pydantic
  - request body
  - error handling
- 실습:
  - `GET /health`
  - `POST /recommend`
  - 더미 추천 결과 반환
  - validation 에러 확인
- 레퍼런스:
  - FastAPI Request Body: [https://fastapi.tiangolo.com/tutorial/body/](https://fastapi.tiangolo.com/tutorial/body/)
  - FastAPI Handling Errors: [https://fastapi.tiangolo.com/tutorial/handling-errors/](https://fastapi.tiangolo.com/tutorial/handling-errors/)
- 4시간 배분:
  - 1h 문서 학습
  - 2h API 구현
  - 1h Swagger/`curl` 테스트

### Day 3. Docker로 FastAPI 컨테이너화
- 학습 목표:
  - API를 컨테이너 이미지로 빌드한다.
  - 로컬 실행과 디버깅을 수행한다.
- 공부 내용:
  - `Dockerfile`
  - 이미지 vs 컨테이너
  - 포트 매핑
- 실습:
  - `Dockerfile` 작성
  - `docker build -t mini-recsys-api .`
  - `docker run -p 8000:8000 mini-recsys-api`
  - `docker logs` 확인
- 레퍼런스:
  - Docker Get Started: [https://docs.docker.com/get-started/](https://docs.docker.com/get-started/)
  - Dockerfile Best Practices: [https://docs.docker.com/develop/develop-images/dockerfile_best-practices/](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- 4시간 배분:
  - 1h 개념
  - 2h 이미지 빌드/실행
  - 1h 디버깅 메모

### Day 4. ECR에 이미지 푸시
- 학습 목표:
  - Docker 이미지를 AWS ECR에 올린다.
  - 이후 서비스 배포 및 운영 자동화의 기반을 만든다.
- 공부 내용:
  - ECR repository
  - image tag
  - login/push flow
- 실습:
  - ECR repository 생성
  - `aws ecr get-login-password`로 로그인
  - 로컬 이미지를 tag 후 push
  - push 확인 후 불필요한 오래된 tag 정리
- 레퍼런스:
  - Amazon ECR getting started: [https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html](https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html)
- 4시간 배분:
  - 1h ECR 개념
  - 2h repository 생성/push
  - 1h 태그 전략 기록

### Day 5. AWS Lambda + API Gateway 실제 배포
- 학습 목표:
  - Lambda 함수와 API Gateway를 실제로 연결한다.
  - 서버리스 API 호출 흐름을 경험한다.
- 공부 내용:
  - Lambda handler
  - event/context
  - API Gateway proxy integration
- 실습:
  - `lambda/lambda_function.py` 작성
  - Lambda 함수 생성
  - API Gateway HTTP API 또는 REST API 연결
  - 실제 endpoint 호출
  - 응답/로그 확인 후 리소스 정리 기준 기록
- 레퍼런스:
  - AWS Lambda Python handler: [https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
  - Building Lambda functions with Python: [https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
  - API Gateway Lambda proxy integration: [https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html)
- 4시간 배분:
  - 1h 문서 학습
  - 2h 함수/API 생성 및 호출
  - 1h CloudWatch 로그 확인
- 종료 체크:
  - 실제 HTTPS endpoint가 응답한다
  - CloudWatch Logs에서 invocation 로그를 확인했다

### Day 6. 서비스 API 역할 정리 + gSASRec 배치 파이프라인 설계
- 학습 목표:
  - `FastAPI 서비스 API`와 `SageMaker ML endpoint`의 책임을 분리한다.
  - 오늘 이후 구현할 end-to-end 흐름의 입력/출력 계약을 고정한다.
- 공부 내용:
  - 서비스 API의 역할
  - ML endpoint의 역할
  - 배치 파이프라인 구성 요소
- 실습:
  - `README.md` 기준 아키텍처를 바탕으로 `FastAPI -> SageMaker endpoint` request/response contract 정의
  - `gSASRec` 입력 스키마 정의:
    - `sequence`
    - `candidate_item_ids`
    - `top_k`
  - 학습/추론/서비스 계층 파일 역할 정의
  - 산출물:
    - `design_doc_v2.md`
    - `data_contract_gsasrec.md`
- 레퍼런스:
  - SageMaker real-time inference: [https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)
  - gSASRec official PyTorch repo: [https://github.com/asash/gSASRec-pytorch](https://github.com/asash/gSASRec-pytorch)
- 4시간 배분:
  - 1h 아키텍처 정리
  - 2h contract 문서화
  - 1h 구현 체크리스트 정리

### Day 7. 공개 로그 데이터 전처리 + SageMaker Processing Job으로 학습 입력 생성
- 학습 목표:
  - 원시 로그를 학습 가능한 시퀀스 데이터로 바꾼다.
  - 전처리를 로컬이 아닌 SageMaker Processing Job으로 실행한다.
  - Processing Job 입력/출력이 S3와 어떻게 연결되는지 이해한다.
- 공부 내용:
  - SageMaker Processing Job 개념 (ScriptProcessor / SKLearnProcessor)
  - ProcessingInput / ProcessingOutput 구조
  - `/opt/ml/processing/input`, `/opt/ml/processing/output` 경로 규약
  - session filtering, item remapping, train/valid/test split
- 실습:
  - `YOOCHOOSE` 클릭 로그 파일을 S3에 업로드 (로컬에서 1회)
  - `sagemaker/preprocess.py` 작성:
    - 세션 길이/아이템 빈도 필터링
    - `item_id -> integer id` 매핑
    - sequence/label 데이터 생성
    - `train.parquet`, `valid.parquet`, `test.parquet` 출력
  - SKLearnProcessor로 Processing Job 실행:
    - input: `s3://.../raw/yoochoose/`
    - output:
      - `s3://.../gsasrec/input/train/`
      - `s3://.../gsasrec/input/valid/`
      - `s3://.../gsasrec/input/test/`
  - CloudWatch Logs에서 Processing Job 로그 확인
  - S3 출력 파일 샘플 검증
- 레퍼런스:
  - YOOCHOOSE challenge overview: [https://recsys.acm.org/recsys15/challenge/](https://recsys.acm.org/recsys15/challenge/)
  - SageMaker Processing Jobs: [https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html](https://docs.aws.amazon.com/sagemaker/latest/dg/processing-job.html)
  - SKLearnProcessor: [https://sagemaker.readthedocs.io/en/stable/frameworks/sklearn/sagemaker.sklearn.html#sagemaker.sklearn.processing.SKLearnProcessor](https://sagemaker.readthedocs.io/en/stable/frameworks/sklearn/sagemaker.sklearn.html#sagemaker.sklearn.processing.SKLearnProcessor)
- 4시간 배분:
  - 1h Processing Job 개념 + 입출력 경로 규약 학습
  - 2h preprocess.py 작성 + Processing Job 실행
  - 1h CloudWatch 로그 확인 + S3 출력 샘플 검증

### Day 8. SageMaker training job으로 gSASRec 학습
- 학습 목표:
  - `gSASRec` 학습을 SageMaker에서 1회 성공시킨다.
  - 최소한의 파라미터로 재현 가능한 training entrypoint를 만든다.
- 공부 내용:
  - PyTorch Estimator
  - training entrypoint
  - hyperparameter 전달
- 실습:
  - `train_gsasrec.py` 작성 또는 official repo script 감싸기
  - 하이퍼파라미터 최소 세트 확정:
    - `sequence_length`
    - `embedding_dim`
    - `num_blocks`
    - `num_heads`
    - `negs_per_pos`
    - `gbce_t`
  - SageMaker training job 실행
  - CloudWatch 로그 확인
  - model artifact 저장 확인
- 레퍼런스:
  - Use PyTorch with SageMaker SDK: [https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html)
  - gSASRec official PyTorch repo: [https://github.com/asash/gSASRec-pytorch](https://github.com/asash/gSASRec-pytorch)
- 4시간 배분:
  - 1h 스크립트 정리
  - 2h training job 실행
  - 1h 로그/결과 점검

### Day 9. 추론 스크립트 구현 + 실시간 endpoint 생성
- 학습 목표:
  - 학습 산출물을 SageMaker 실시간 endpoint로 배포할 수 있게 만든다.
  - `model_fn`, `input_fn`, `predict_fn`, `output_fn` 기준으로 추론 API를 고정한다.
- 공부 내용:
  - real-time inference script
  - endpoint config
  - invoke payload
- 실습:
  - `sagemaker/inference.py` 작성
  - 입력 예시:
    - `{"sequence": [12, 55, 91, 103], "candidate_item_ids": [201, 305, 411], "top_k": 10}`
  - 출력 예시:
    - `{"item_ids": [...], "scores": [...]}`
  - SageMaker model 생성
  - endpoint config 생성
  - real-time endpoint 1차 배포
  - 샘플 payload로 invoke
- 레퍼런스:
  - Deploy a PyTorch model: [https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#deploy-a-pytorch-model](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#deploy-a-pytorch-model)
  - SageMaker real-time endpoints: [https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)
- 4시간 배분:
  - 1h inference script 작성
  - 2h endpoint 생성/호출
  - 1h 입력/출력 검증

### Day 10. SageMaker Pipelines로 전처리→학습→배포 파이프라인 구성
- 학습 목표:
  - Day 7~9에서 개별로 실행한 Processing/Training/Endpoint 단계를 하나의 파이프라인으로 연결한다.
  - 파이프라인을 재실행 가능한 MLOps 자동화 단위로 만든다.
- 공부 내용:
  - SageMaker Pipelines 개념 (Pipeline, Step, PipelineSession)
  - ProcessingStep / TrainingStep / CreateModelStep / UpdateEndpointStep
  - 파이프라인 파라미터 (ParameterString, ParameterInteger)
  - 파이프라인 실행 및 모니터링
- 실습:
  - `sagemaker/pipeline.py` 작성
  - ProcessingStep: Day 7의 `preprocess.py`를 step으로 래핑
  - TrainingStep: Day 8의 training job을 step으로 래핑
  - CreateModelStep: 학습 artifact로 모델 생성
  - UpdateEndpointStep: 새 모델로 endpoint 갱신
  - 파이프라인 실행 및 Console에서 DAG 확인
  - 파이프라인 재실행 테스트 (파라미터 변경 후 재실행)
- 레퍼런스:
  - SageMaker Pipelines: [https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html)
  - SageMaker Pipelines SDK: [https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html](https://sagemaker.readthedocs.io/en/stable/workflows/pipelines/sagemaker.workflow.pipelines.html)
- 4시간 배분:
  - 1h Pipelines 개념 + Step 구조 학습
  - 2h pipeline.py 작성 + 파이프라인 실행
  - 1h Console DAG 확인 + 재실행 테스트

### Day 11. endpoint refresh, warm-up, 점진 배포, cutover 구현
- 학습 목표:
  - 새 모델 버전으로 endpoint를 안전하게 교체하는 흐름을 구현한다.
  - 운영 환경에서 필요한 refresh/warm-up/cutover 개념을 실제 절차로 정리한다.
- 공부 내용:
  - new model version
  - new endpoint config
  - endpoint update
  - warm-up invoke
  - gradual rollout / cutover / rollback
- 실습:
  - 새 model artifact 또는 새 endpoint config 생성
  - endpoint update 수행
  - warm-up 요청 여러 건 보내기
  - variant 또는 새 config 기준 트래픽 전환 방식 정리
  - rollback 절차 `aws_runbook.md`에 기록
  - 최소 수준으로 blue/green 또는 canary 개념을 문서/절차로 구현
- 레퍼런스:
  - SageMaker endpoint update: [https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)
  - Shadow tests and deployment guardrails: [https://docs.aws.amazon.com/sagemaker/latest/dg/deployment-guardrails.html](https://docs.aws.amazon.com/sagemaker/latest/dg/deployment-guardrails.html)
- 4시간 배분:
  - 1h 개념 정리
  - 2h endpoint update/warm-up 실습
  - 1h cutover/rollback 문서화

### Day 12. autoscaling 설정 + endpoint 부하 테스트
- 학습 목표:
  - endpoint의 scale-out/scale-in을 설정하고 기본 동작을 확인한다.
  - endpoint 자체 latency와 TPS를 측정한다.
- 공부 내용:
  - Application Auto Scaling
  - target tracking
  - endpoint latency / invocation metric
- 실습:
  - autoscaling policy 설정
  - min/max instance 설정
  - 부하 테스트 도구로 endpoint 호출:
    - `hey`, `ab`, 또는 간단한 Python script
  - 측정 항목:
    - p50/p95 latency
    - error rate
    - invocation count
  - CloudWatch metric 확인
- 레퍼런스:
  - SageMaker autoscaling: [https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling-policy.html](https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling-policy.html)
  - CloudWatch metrics for endpoints: [https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-cloudwatch.html](https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-cloudwatch.html)
- 4시간 배분:
  - 1h autoscaling 설정
  - 2h 부하 테스트
  - 1h CloudWatch metric 해석

### Day 13. FastAPI 서비스 API에서 SageMaker endpoint 호출 + E2E 테스트
- 학습 목표:
  - `FastAPI`를 진짜 서비스 API로 리팩터링한다.
  - `FastAPI -> SageMaker endpoint -> FastAPI response` end-to-end 흐름을 완성한다.
- 공부 내용:
  - SageMaker runtime client
  - request transformation
  - timeout / retry / fallback
- 실습:
  - `app/main.py`와 `app/recommender.py` 수정
  - FastAPI 입력은 서비스 관점으로 유지:
    - `user_id`
    - `query` 또는 `candidate source`
    - `top_k`
  - 내부에서:
    - 사용자 sequence 준비
    - candidate list 준비
    - SageMaker endpoint payload 생성
    - endpoint invoke
    - score 수신 후 응답 반환
  - timeout 또는 5xx 시 fallback 응답 구현
  - E2E 테스트:
    - client -> FastAPI -> SageMaker -> response
  - 가능하면 FastAPI 경유 부하 테스트 1회 수행
- 레퍼런스:
  - InvokeEndpoint API: [https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sagemaker-runtime/client/invoke_endpoint.html](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sagemaker-runtime/client/invoke_endpoint.html)
  - FastAPI testing: [https://fastapi.tiangolo.com/tutorial/testing/](https://fastapi.tiangolo.com/tutorial/testing/)
- 4시간 배분:
  - 1h 서비스 API 구조 수정
  - 2h SageMaker 연동 구현
  - 1h E2E 테스트와 fallback 확인

### Day 14. 최종 통합: AWS 아키텍처, 운영 전략, 면접 답변 정리
- 학습 목표:
  - 모든 컴포넌트를 하나의 운영 아키텍처로 연결해 설명한다.
  - 실무와 면접 둘 다 대응 가능한 문서를 만든다.
- 공부 내용:
  - FastAPI direct serving vs Lambda vs SageMaker
  - 비용/지연시간/운영복잡도 trade-off
  - rollback/fallback/monitoring
- 실습:
  - `design_doc_final.md` 작성
  - 아키텍처 다이어그램 작성
  - 예상 질문 10개와 답변 초안 작성
- 레퍼런스:
  - Day 1~12 자료 전체 재사용
- 4시간 배분:
  - 2h 문서화
  - 1h 아키텍처 비교 정리
  - 1h 예상 질문 답변 작성

## 4. 반드시 해봐야 할 AWS 실습
- ECR repository를 직접 만들고 이미지를 push했다.
- Lambda 함수를 직접 만들고 API Gateway로 호출했다.
- CloudWatch Logs에서 Lambda 호출 로그를 확인했다.
- SageMaker endpoint를 직접 만들고 invoke한 뒤 삭제했다.
- CI에서 Docker build와 ECR push 또는 build 검증을 수행했다.

## 5. 비용/안전 원칙
- SageMaker endpoint는 실습이 끝나면 반드시 삭제한다.
- 불필요한 Lambda/API Gateway/ECR 테스트 리소스도 정리한다.
- 가능하면 작은 instance/type을 사용한다.
- `aws_runbook.md`에 생성 리소스와 삭제 명령을 같이 남긴다.

## 6. 면접 대비 포인트
- `Lambda`는 경량 API, 이벤트 기반 처리, burst 트래픽에 유리한 케이스로 설명한다.
- `SageMaker Endpoint`는 모델 전용 managed serving, autoscaling, inference 운영 관점으로 설명한다.
- `FastAPI + Docker`는 서비스 로직 유연성과 개발 속도 측면으로 설명한다.
- 모델은 깊게 들어가기보다 "추천 파이프라인 안에서 어떤 위치에 있고, 어떻게 서빙/리랭킹에 연결되는가" 중심으로 설명한다.
