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

# 기본 설정만 (Kubernetes 도구 제거됨)

# 기타 설정
ENV=development
PORT=8080
LOG_LEVEL=INFO
```

### 🚨 보안 주의사항

**절대 하드코딩하지 말 것:**
- VLLM 서버 접속 정보
- API 키나 토큰
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

### MCP 도구들 (간소화됨)
- **시간**: 지역별 시간 조회
- **HTTP**: GET/POST 요청
- **VLLM**: 모델 조회, 채팅 API
- **계산**: 수학 계산

### OSS 모델 도구 사용
- 일부 오픈소스 모델은 최신 `tools` 필드를 지원하지 않아 500 오류가 발생할 수 있습니다.
- 클라이언트는 자동으로 기존 `functions` 필드로 재시도하여 도구 호출을 시도합니다.

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
