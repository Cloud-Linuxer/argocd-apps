"""단순 채팅용 FastAPI 백엔드"""

import json
import asyncio
import logging
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_vllm_config
from vllm_client import VLLMClient
from mcp_tools import MCPTools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="VLLM Chat Backend", version="3.0.6")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vllm_client: Optional[VLLMClient] = None
mcp_tools: Optional[MCPTools] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI 응답")


@app.on_event("startup")
async def startup() -> None:
    global vllm_client, mcp_tools
    config = get_vllm_config()
    vllm_client = VLLMClient(
        config["base_url"],
        config["model"],
        max_tokens=config.get("max_tokens", 1000),
        temperature=config.get("temperature", 0.7),
        timeout=config.get("timeout", 60),
    )
    mcp_tools = MCPTools()


@app.on_event("shutdown")
async def shutdown() -> None:
    if vllm_client:
        await vllm_client.close()
    if mcp_tools:
        await mcp_tools.close()


SYSTEM_PROMPT = (
    "You are a helpful assistant with tool-use abilities. "
    "When the user asks for factual, current, or external information, prefer using tools. "
    "For time queries, call get_current_time with an appropriate timezone. "
    "Always return concise answers."
)


def _looks_like_time_query(text: str) -> bool:
    t = text.lower()
    keywords = [
        "time",
        "현재시간",
        "지금 시간",
        "몇 시",
        "몇시",
        "what time",
        "현재 시각",
    ]
    return any(k in t for k in keywords)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not vllm_client or not mcp_tools:
        raise HTTPException(status_code=500, detail="Server not initialized")
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": request.message},
    ]
    try:
        tool_choice = None
        if _looks_like_time_query(request.message):
            # Force the model to call the time tool
            tool_choice = {"type": "function", "function": {"name": "get_current_time"}}

        response = await vllm_client.chat(
            messages,
            tools=mcp_tools.get_schemas(),
            tool_choice=tool_choice,
        )
        msg = response["choices"][0]["message"]
        logger.debug("model message: %s", msg)

        if "tool_calls" in msg:
            messages.append(msg)
            for call in msg["tool_calls"]:
                try:
                    name = call["function"]["name"]
                    args = call["function"].get("arguments") or "{}"
                    call_id = call.get("id", "unknown")
                    
                    # JSON 파싱 안전하게 처리
                    try:
                        params = json.loads(args)
                    except json.JSONDecodeError as e:
                        result = f"Invalid JSON arguments: {e}"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": result,
                        })
                        continue
                    
                    func = getattr(mcp_tools, name, None)
                    if not func:
                        result = f"Unknown tool: {name}"
                    else:
                        try:
                            if asyncio.iscoroutinefunction(func):
                                result = await func(**params)
                            else:
                                result = func(**params)
                            
                            # 결과를 문자열로 변환
                            if not isinstance(result, str):
                                result = str(result)
                                
                        except Exception as e:
                            logger.error(f"Tool execution error for {name}: {e}")
                            result = f"Tool execution failed: {e}"
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": result,
                    })
                    
                except Exception as e:
                    logger.error(f"Tool call processing error: {e}")
                    # 기본 오류 응답 추가
                    messages.append({
                        "role": "tool", 
                        "tool_call_id": call.get("id", "error"),
                        "name": call.get("function", {}).get("name", "unknown"),
                        "content": f"Tool call processing failed: {e}"
                    })
            logger.debug("messages before follow-up: %s", [m.get("role") for m in messages])
            followup = await vllm_client.chat(messages)
            final = followup["choices"][0]["message"].get("content", "")
            return ChatResponse(response=final)
        else:
            return ChatResponse(response=msg.get("content", ""))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed")


@app.get("/api/tools")
async def get_tools() -> dict:
    """등록된 도구 목록 반환"""
    if not mcp_tools:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    schemas = mcp_tools.get_schemas()
    tools_info = []
    
    for schema in schemas:
        func_info = schema["function"]
        tools_info.append({
            "name": func_info["name"],
            "description": func_info["description"],
            "parameters": func_info.get("parameters", {})
        })
    
    return {
        "tools": tools_info,
        "count": len(tools_info)
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}