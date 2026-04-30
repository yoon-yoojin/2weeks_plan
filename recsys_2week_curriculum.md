# 13일 집중 커리큘럼 (AWS 실계정 기반 RecSys Serving Engineering + Ops)

## 0. 목표
- 기간: 13일
- 학습 시간: 하루 4시간
- 방향:
  - 모델링은 1일로 압축
  - `FastAPI`, `Docker`, `AWS Lambda`, `API Gateway`, `ECR`, `SageMaker`, `Argo CD`를 실제 실습 중심으로 학습
  - 최종적으로 "추천 API를 로컬과 AWS에서 모두 띄우고, 배포/운영/롤백 흐름까지 설명 가능한 상태"를 만든다

## 1. 전제
- AWS 실계정이 있고, 기본적인 콘솔 접근 및 `aws cli` 사용이 가능하다고 가정한다.
- 비용 통제를 위해 실습은 작은 리소스로 진행하고, 각 Day에 `삭제` 단계를 포함한다.
- Argo CD는 AWS에서는 `EKS`가 가장 자연스럽지만, 13일/하루 4시간 기준으로는 `로컬 K8s + Argo CD` 또는 `기존 K8s 환경` 전제를 권장한다.
- 실습 전에 최소 준비:
  - `aws configure`
  - 기본 region 확정
  - `Docker` 설치
  - `kubectl` 설치
  - 가능하면 `kind` 또는 `minikube` 설치

## 2. 최종 산출물
- `mini-recsys-serving/`
  - `app/main.py`: FastAPI 추천 API
  - `app/recommender.py`: 추천 + fallback 로직
  - `app/schemas.py`: request/response schema
  - `Dockerfile`
  - `.github/workflows/ci.yml`
  - `lambda/lambda_function.py`
  - `sagemaker/inference.py`
  - `k8s/deployment.yaml`
  - `k8s/service.yaml`
  - `argocd/application.yaml`
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
  - 이후 Lambda container image 또는 K8s/EKS 배포의 기반을 만든다.
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

### Day 6. 모델링 1일 압축: DeepFM / SASRec / 리랭킹 구조 설명 가능 상태 만들기
- 학습 목표:
  - 모델 자체를 깊게 구현하기보다 서비스 파이프라인 안에서의 역할을 설명할 수 있게 만든다.
- 공부 내용:
  - DeepFM: 1차 점수
  - SASRec 계열: 시퀀스 기반 재정렬
  - late fusion
  - fallback
- 실습:
  - 더미 점수 함수 2개 작성
  - `final_score = a * deepfm_score + b * seq_score`
  - 리랭킹 전후 top-k 비교
- 레퍼런스:
  - DeepFM: [https://www.ijcai.org/Proceedings/2017/239](https://www.ijcai.org/Proceedings/2017/239)
  - SASRec: [https://arxiv.org/abs/1808.09781](https://arxiv.org/abs/1808.09781)
- 4시간 배분:
  - 2h 모델 구조 이해
  - 1h 결합 예제 구현
  - 1h 이력서 설명 문장 정리

### Day 7. 추천 API 내부 흐름과 fallback 구현
- 학습 목표:
  - 추천 요청 처리 로직을 서비스 코드로 구현한다.
  - cold-start, missing-profile, timeout fallback을 넣는다.
- 공부 내용:
  - candidate 생성
  - scoring
  - rerank
  - fallback
- 실습:
  - `app/recommender.py` 작성
  - fallback 3종 구현
  - 응답에 `fallback_used` 포함
- 레퍼런스:
  - FastAPI Testing: [https://fastapi.tiangolo.com/tutorial/testing/](https://fastapi.tiangolo.com/tutorial/testing/)
- 4시간 배분:
  - 1h 로직 설계
  - 2h 구현
  - 1h 실패 케이스 점검

### Day 8. 테스트, 로깅, CloudWatch/운영 메트릭 설계
- 학습 목표:
  - API를 운영 가능한 형태로 만든다.
  - 어떤 로그와 메트릭을 봐야 하는지 정한다.
- 공부 내용:
  - request id
  - latency
  - error rate
  - fallback rate
  - model version
- 실습:
  - `pytest` 테스트 추가
  - 구조화 로그 추가
  - CloudWatch에서 보고 싶은 메트릭 목록 작성
- 레퍼런스:
  - FastAPI Testing: [https://fastapi.tiangolo.com/tutorial/testing/](https://fastapi.tiangolo.com/tutorial/testing/)
  - CloudWatch Logs docs: [https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html)
- 4시간 배분:
  - 1h 테스트 설계
  - 2h 테스트/로그 구현
  - 1h 운영 메트릭 문서화

### Day 9. SageMaker real-time endpoint 실제 배포
- 학습 목표:
  - SageMaker endpoint를 실제로 생성, 호출, 삭제한다.
  - 이력서의 `SageMaker Endpoint` 항목을 실체적으로 이해한다.
- 공부 내용:
  - model artifact
  - inference script
  - endpoint config
  - real-time endpoint
- 실습:
  - `sagemaker/inference.py` 작성
  - 가능한 최소 모델 artifact 준비
  - SageMaker model 생성
  - endpoint config 생성
  - endpoint 배포 및 invoke
  - 실습 종료 후 endpoint 삭제
- 레퍼런스:
  - SageMaker real-time inference: [https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)
  - SageMaker Python SDK inference docs: [https://sagemaker.readthedocs.io/en/stable/inference/index.html](https://sagemaker.readthedocs.io/en/stable/inference/index.html)
- 4시간 배분:
  - 1h 구조 학습
  - 2h 생성/호출 실습
  - 1h 삭제 및 비용 메모
- 종료 체크:
  - endpoint invoke 성공
  - endpoint/model/config 삭제 완료

### Day 10. SageMaker autoscaling, versioning, 운영 runbook 작성
- 학습 목표:
  - endpoint를 띄우는 것에서 끝나지 않고 운영 관점을 정리한다.
- 공부 내용:
  - autoscaling
  - versioning
  - rollback
  - canary/alpha rollout 개념
- 실습:
  - autoscaling 정책 문서 읽고 정리
  - endpoint 운영 runbook 작성
  - "생성 -> 검증 -> 배포 -> 롤백 -> 삭제" 절차 문서화
- 레퍼런스:
  - SageMaker real-time inference autoscaling: [https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)
- 4시간 배분:
  - 1.5h 문서 학습
  - 1.5h runbook 작성
  - 1h 면접용 답변 메모

### Day 11. CI/CD: GitHub Actions로 test + Docker build + ECR push 자동화
- 학습 목표:
  - 코드 변경 시 자동 검증과 이미지 빌드를 수행한다.
  - 배포 전 기본 품질 게이트를 만든다.
- 공부 내용:
  - GitHub Actions
  - AWS credentials in CI
  - Docker build/push
- 실습:
  - `.github/workflows/ci.yml` 작성
  - `pytest`
  - Docker image build
  - 가능하면 ECR push까지 자동화
- 레퍼런스:
  - GitHub Actions docs: [https://docs.github.com/en/actions](https://docs.github.com/en/actions)
  - Amazon ECR getting started: [https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html](https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html)
- 4시간 배분:
  - 1h CI 개념
  - 2h workflow 구현
  - 1h 실행 로그 점검

### Day 12. Kubernetes + Argo CD 실습
- 학습 목표:
  - GitOps 배포 흐름을 직접 경험한다.
  - Argo CD가 운영에 왜 필요한지 체감한다.
- 공부 내용:
  - Deployment
  - Service
  - Argo CD Application
  - sync/rollback
- 실습:
  - `kind` 또는 `minikube` 클러스터 준비
  - Argo CD 설치
  - FastAPI 배포용 `deployment.yaml`, `service.yaml` 작성
  - `argocd/application.yaml` 작성
  - git 변경 -> sync 확인
- 레퍼런스:
  - Argo CD Getting Started: [https://argo-cd.readthedocs.io/en/release-3.4/getting_started/](https://argo-cd.readthedocs.io/en/release-3.4/getting_started/)
  - Kubernetes basics: [https://kubernetes.io/docs/tutorials/kubernetes-basics/](https://kubernetes.io/docs/tutorials/kubernetes-basics/)
- 4시간 배분:
  - 1.5h K8s/Argo CD 설치
  - 1.5h manifest/application 적용
  - 1h sync 흐름 기록

### Day 13. 최종 통합: AWS 아키텍처, 운영 전략, 면접 답변 정리
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
- `Argo CD`는 GitOps, 배포 이력, drift 방지, 롤백 가능성과 연결한다.
- 모델은 깊게 들어가기보다 "추천 파이프라인 안에서 어떤 위치에 있고, 어떻게 서빙/리랭킹에 연결되는가" 중심으로 설명한다.
