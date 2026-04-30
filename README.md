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
├── recsys_4week_curriculum.md   # 13일 상세 커리큘럼
├── day1/                        # Day 1 실습 자료
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
