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


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not vllm_client or not mcp_tools:
        raise HTTPException(status_code=500, detail="Server not initialized")
    messages: List[Dict[str, str]] = [{"role": "user", "content": request.message}]
    try:
        response = await vllm_client.chat(messages, tools=mcp_tools.get_schemas())
        msg = response["choices"][0]["message"]

        if "tool_calls" in msg:
            messages.append(msg)
            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                args = call["function"].get("arguments") or "{}"
                params = json.loads(args)
                func = getattr(mcp_tools, name, None)
                if not func:
                    result = f"Unknown tool: {name}"
                else:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(**params)
                    else:
                        result = func(**params)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": result,
                    }
                )
            followup = await vllm_client.chat(messages)
            final = followup["choices"][0]["message"].get("content", "")
            return ChatResponse(response=final)
        else:
            return ChatResponse(response=msg.get("content", ""))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
