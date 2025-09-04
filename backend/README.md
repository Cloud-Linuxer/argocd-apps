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

### 🧪 빠른 사용 예시 (cURL)

```bash
# 1) gpt-oss 모델과 채팅 (툴 사용 가능)
curl -sS -X POST http://localhost:8080/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "https://example.com 을 GET 요청해줘"}' | jq .

# 2) LangChain 에이전트 대화 (ReAct)
curl -sS -X POST http://localhost:8080/api/agent_chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "현재 서울 시간을 알려줘"}' | jq .

# 3) 등록된 도구 목록 확인
curl -sS http://localhost:8080/api/tools | jq .
```

#### Responses API 툴 호출 예시

```bash
# 툴 등록 + 질문
curl -sS -X POST "$BASE/v1/responses" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{
  "model": "openai/gpt-oss-20b",
  "input": "서울 날씨 어때?",
  "tools": [
    {"type":"function","name":"get_weather","parameters":{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}}
  ]
}'

# 응답에서 function_call 의 call_id 와 arguments 파싱 후 툴 실행 → 결과 전달
curl -sS -X POST "$BASE/v1/responses" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d "{
  \"model\": \"openai/gpt-oss-20b\",
  \"previous_response_id\": \"${RESP_ID}\",
  \"input\": [{\"type\":\"function_call_output\",\"call_id\":\"${CALL_ID}\",\"output\":\"{\\\"city\\\":\\\"Seoul\\\",\\\"temp_c\\\":27}\"}],
  \"tools\": [{\"type\":\"function\",\"name\":\"get_weather\",\"parameters\":{\"type\":\"object\",\"properties\":{\"city\":{\"type\":\"string\"}},\"required\":[\"city\"]}}]
}"
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
- **http_request**: 사내/외부 HTTP API 호출
- **time_now**: 지정된 시간대의 현재 시각 반환

### OSS 모델 도구 사용
- 일부 오픈소스 모델은 최신 `tools` 필드를 지원하지 않아 500 오류가 발생할 수 있습니다.
- 클라이언트는 자동으로 기존 `functions` 필드로 재시도하여 도구 호출을 시도합니다.

### API 엔드포인트
- `GET /health` - 서비스 상태
- `GET /api/tools` - 등록된 도구 목록
- `POST /api/chat` - gpt-oss 모델과 채팅 (툴 사용)
- `POST /api/agent_chat` - LangChain ReAct 에이전트와 채팅 (vLLM OpenAI API 사용)

## 🔒 보안

이 애플리케이션은 민감한 정보에 접근할 수 있으므로:

1. **환경변수로만** 민감한 정보 관리
2. **네트워크 보안** 설정 (VPN, 방화벽)
3. **접근 권한** 최소화
4. **로그 모니터링** 필수
5. **정기적인 보안 업데이트**


