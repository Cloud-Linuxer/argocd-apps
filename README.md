# ArgoCD Applications Repository

이 저장소는 ArgoCD를 통한 GitOps 배포를 위한 애플리케이션 매니페스트를 포함합니다.

## 구조
- `applications/`: ArgoCD Application 정의
- `manifests/`: Kubernetes 매니페스트 파일들

## 사용법
1. 이 저장소를 GitHub에 푸시
2. ArgoCD에서 애플리케이션 등록
3. 자동 동기화 활성화
