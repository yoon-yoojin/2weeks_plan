# RecSys Serving Engineering — 13일 집중 커리큘럼

추천 API를 로컬과 AWS에서 실제로 배포·운영·롤백하는 것을 목표로 하는 13일 실습 프로젝트입니다.

## 학습 목표

- FastAPI로 추천 API 구현
- Docker 컨테이너화 및 AWS ECR push
- AWS Lambda / API Gateway / SageMaker 배포
- Argo CD를 이용한 GitOps 운영

## 디렉토리 구조

```
4weeks_plan/
├── recsys_2week_curriculum.md      # 13일 상세 커리큘럼
├── day1/
│   └── day1_submit.md              # POST /recommend API 명세 (ML ranking API 기준)
├── mini-recsys-serving/            # Day 2~ FastAPI 구현체
│   ├── app/
│   │   ├── main.py                 # FastAPI 앱, 라우터, exception handler
│   │   ├── schemas.py              # Pydantic request/response 모델
│   │   ├── recommender.py          # 더미 scoring 로직
│   │   └── errors.py               # 커스텀 에러 클래스
│   └── requirements.txt
└── README.md
```

## 사전 준비

- `aws configure` 완료
- Docker, kubectl 설치
- `kind` 또는 `minikube` (로컬 K8s)

## 최종 산출물

| 파일 | 설명 |
|------|------|
| `mini-recsys-serving/` | FastAPI 앱, Lambda, SageMaker, K8s 매니페스트 |
| `aws_runbook.md` | Lambda/ECR/SageMaker 배포 절차 |
| `design_doc_final.md` | API 흐름, AWS 아키텍처, 비용/롤백 전략 |

## 진행 현황

| Day | 주제 | 상태 |
|-----|------|------|
| Day 1 | HTTP/REST/FastAPI 기본과 추천 API 계약 정의 | 완료 |
| Day 2 | FastAPI 추천 API 구현 | 완료 |
| Day 3 | Docker로 FastAPI 컨테이너화 | - |
| Day 4 | ECR에 이미지 푸시 | - |
| Day 5 | AWS Lambda + API Gateway 실제 배포 | - |
| Day 6 | 모델링 1일 압축 | - |
| Day 7 | 추천 API 내부 흐름과 fallback 구현 | - |
| Day 8 | 테스트, 로깅, CloudWatch/운영 메트릭 설계 | - |
| Day 9 | SageMaker real-time endpoint 실제 배포 | - |
| Day 10 | SageMaker autoscaling, versioning, 운영 runbook | - |
| Day 11 | CI/CD: GitHub Actions 자동화 | - |
| Day 12 | Kubernetes + Argo CD 실습 | - |
| Day 13 | 최종 통합: AWS 아키텍처, 운영 전략, 면접 답변 정리 | - |
