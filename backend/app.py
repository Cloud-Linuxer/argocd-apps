"""
VLLM 펑션콜 에이전트 백엔드 API
FastAPI 기반의 AI 에이전트 서비스
"""

import logging
import os
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from agent import VLLMClient, FunctionCallAgent
from mcp_tools import MCPTools

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 전역 변수
vllm_client: Optional[VLLMClient] = None
agent: Optional[FunctionCallAgent] = None
mcp_tools: Optional[MCPTools] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global vllm_client, agent, mcp_tools
    
    # 시작 시 초기화
    logger.info("VLLM 에이전트 초기화 중...")
    
    try:
        # VLLM 클라이언트 초기화 (환경변수 필수!)
        from config import get_vllm_config
        vllm_config = get_vllm_config()
        
        vllm_client = VLLMClient(
            base_url=vllm_config["base_url"], 
            model=vllm_config["model"]
        )
        
        # MCP 도구 초기화
        mcp_tools = MCPTools()
        
        # 에이전트 초기화
        system_prompt = """
당신은 VLLM 기반 AI 어시스턴트입니다.
사용자의 요청에 따라 제공된 도구들을 사용하여 다음과 같은 작업을 수행할 수 있습니다:

- HTTP 요청 수행
- VLLM API 호출  
- 수학 계산
- 시간 조회

도구를 사용할 때는 JSON 형식으로 명확하게 요청하고, 결과를 바탕으로 사용자에게 유용한 정보를 제공하세요.
"""
        
        agent = FunctionCallAgent(
            vllm_client=vllm_client,
            system_prompt=system_prompt,
            max_iterations=10
        )
        
        # MCP 도구들을 에이전트에 등록
        for tool in mcp_tools.get_all_tools():
            agent.add_tool(tool)
        
        logger.info(f"에이전트 초기화 완료 - {len(agent.tools)}개 도구 등록됨")
        
        yield
        
    except Exception as e:
        logger.error(f"초기화 오류: {e}")
        raise
    
    finally:
        # 종료 시 정리
        logger.info("리소스 정리 중...")
        if vllm_client:
            await vllm_client.close()
        if mcp_tools:
            await mcp_tools.close()


# FastAPI 앱 생성
app = FastAPI(
    title="VLLM Function Call Agent",
    description="VLLM 기반 펑션콜 에이전트 API",
    version="3.0.3",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic 모델들
class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")
    clear_history: bool = Field(default=False, description="대화 기록 초기화 여부")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI 응답")
    conversation_id: str = Field(..., description="대화 ID")
    tools_used: List[str] = Field(default_factory=list, description="사용된 도구 목록")


class HealthResponse(BaseModel):
    status: str = Field(..., description="서비스 상태")
    service: str = Field(..., description="서비스 이름")
    version: str = Field(..., description="서비스 버전")
    vllm_connected: bool = Field(..., description="VLLM 연결 상태")
    tools_count: int = Field(..., description="등록된 도구 수")


class ToolInfo(BaseModel):
    name: str = Field(..., description="도구 이름")
    description: str = Field(..., description="도구 설명")
    tool_type: str = Field(..., description="도구 타입")
    parameters: Dict[str, Any] = Field(..., description="도구 파라미터")


class ModelsResponse(BaseModel):
    models: List[Dict[str, Any]] = Field(..., description="사용 가능한 모델 목록")


# API 엔드포인트들

@app.get("/health", response_model=HealthResponse)
async def health():
    """서비스 상태 확인"""
    try:
        vllm_connected = False
        tools_count = 0
        
        if vllm_client:
            try:
                await vllm_client.get_models()
                vllm_connected = True
            except:
                pass
        
        if agent:
            tools_count = len(agent.tools)
        
        return HealthResponse(
            status="healthy",
            service="vllm-function-call-agent",
            version="3.0.3",
            vllm_connected=vllm_connected,
            tools_count=tools_count
        )
    
    except Exception as e:
        logger.error(f"헬스체크 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/info")
async def info():
    """서비스 정보 반환"""
    from config import get_settings, get_vllm_config
    settings = get_settings()
    vllm_config = get_vllm_config()
    
    return {
        "service": "vllm-function-call-agent",
        "version": "3.0.3",
        "environment": settings.env,
        "vllm_base_url": vllm_config["base_url"],
        "vllm_model": vllm_config["model"]
    }


@app.get("/api/models", response_model=ModelsResponse)
async def get_models():
    """사용 가능한 VLLM 모델 조회"""
    try:
        if not vllm_client:
            raise HTTPException(status_code=500, detail="VLLM 클라이언트가 초기화되지 않았습니다.")
        
        models_data = await vllm_client.get_models()
        return ModelsResponse(models=models_data.get("data", []))
    
    except Exception as e:
        logger.error(f"모델 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tools", response_model=List[ToolInfo])
async def get_tools():
    """등록된 도구 목록 조회"""
    try:
        if not agent:
            raise HTTPException(status_code=500, detail="에이전트가 초기화되지 않았습니다.")
        
        tools_info = []
        for tool in agent.tools.values():
            tools_info.append(ToolInfo(
                name=tool.name,
                description=tool.description,
                tool_type=tool.tool_type.value,
                parameters=tool.parameters
            ))
        
        return tools_info
    
    except Exception as e:
        logger.error(f"도구 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """에이전트와 채팅"""
    try:
        if not agent:
            raise HTTPException(status_code=500, detail="에이전트가 초기화되지 않았습니다.")
        
        # 대화 기록 초기화 요청 시
        if request.clear_history:
            agent.clear_history()
            logger.info("대화 기록이 초기화되었습니다.")
        
        # 에이전트와 채팅
        response = await agent.chat(request.message)
        
        return ChatResponse(
            response=response,
            conversation_id="default",  # 추후 세션 관리 구현 시 사용
            tools_used=[]  # 추후 사용된 도구 추적 구현
        )
    
    except Exception as e:
        logger.error(f"채팅 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversation")
async def get_conversation():
    """현재 대화 기록 조회"""
    try:
        if not agent:
            raise HTTPException(status_code=500, detail="에이전트가 초기화되지 않았습니다.")
        
        return {
            "conversation_history": agent.get_conversation_history(),
            "tools_count": len(agent.tools)
        }
    
    except Exception as e:
        logger.error(f"대화 기록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversation")
async def clear_conversation():
    """대화 기록 초기화"""
    try:
        if not agent:
            raise HTTPException(status_code=500, detail="에이전트가 초기화되지 않았습니다.")
        
        agent.clear_history()
        return {"message": "대화 기록이 초기화되었습니다."}
    
    except Exception as e:
        logger.error(f"대화 기록 초기화 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 메인 실행
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV", "development") == "development"
    )
