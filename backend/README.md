# VLLM Function Call Agent

VLLM 기반 펑션콜 에이전트 백엔드 서비스

## 🔧 환경 설정

### 필수 환경변수

다음 환경변수들을 설정해야 합니다:

```bash
# VLLM 설정
VLLM_BASE_URL=http://your-vllm-server:port
VLLM_MODEL=your-model-name
VLLM_MAX_TOKENS=1000
VLLM_TEMPERATURE=0.7

# Kubernetes 설정 (민감 정보!)
K8S_HOST=your-k8s-host
K8S_USER=your-k8s-user
K8S_PASSWORD=your-k8s-password

# 기타 설정
ENV=development
PORT=8080
LOG_LEVEL=INFO
```

### 🚨 보안 주의사항

**절대 하드코딩하지 말 것:**
- Kubernetes 접속 정보 (호스트, 사용자, 비밀번호)
- API 키나 토큰
- 데이터베이스 연결 정보
- 기타 민감한 설정값들

**권장 방법:**
1. `.env` 파일 사용 (gitignore에 포함됨)
2. 컨테이너 환경변수
3. Kubernetes Secrets
4. 외부 설정 관리 시스템

### 📦 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정 후 실행
python app.py
```

### 🐳 Docker 실행

```bash
# 빌드
docker build -t vllm-function-agent .

# 실행 (환경변수 전달)
docker run -d -p 8080:8080 \
  -e VLLM_BASE_URL=http://your-vllm-server:port \
  -e VLLM_MODEL=your-model-name \
  -e K8S_HOST=your-k8s-host \
  -e K8S_USER=your-k8s-user \
  -e K8S_PASSWORD=your-k8s-password \
  --name vllm-agent vllm-function-agent
```

## 🛠️ 기능

### MCP 도구들
- **시스템**: 시간, 시스템 정보
- **파일**: 파일 읽기/쓰기, 디렉토리 나열
- **HTTP**: GET/POST 요청
- **Kubernetes**: 파드/서비스 조회
- **VLLM**: 모델 조회, 채팅 API
- **계산**: 수학 계산

### API 엔드포인트
- `GET /health` - 서비스 상태
- `GET /api/info` - 서비스 정보
- `GET /api/tools` - 등록된 도구 목록
- `POST /api/chat` - 에이전트와 채팅
- `GET /api/conversation` - 대화 기록
- `DELETE /api/conversation` - 대화 기록 초기화

## 🔒 보안

이 애플리케이션은 민감한 정보에 접근할 수 있으므로:

1. **환경변수로만** 민감한 정보 관리
2. **네트워크 보안** 설정 (VPN, 방화벽)
3. **접근 권한** 최소화
4. **로그 모니터링** 필수
5. **정기적인 보안 업데이트**
