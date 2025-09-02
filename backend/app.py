"""단순 채팅용 FastAPI 백엔드"""

import json
import asyncio
import logging
from typing import Optional, List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_vllm_config, get_settings
from vllm_client import VLLMClient
from mcp_tools import MCPTools
from typing import Any

try:
    # LangChain integration (optional at import time)
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.tools import tool
    _LANGCHAIN_AVAILABLE = True
except Exception:
    _LANGCHAIN_AVAILABLE = False

settings = get_settings()
_level_name = (settings.log_level or "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)
logging.basicConfig(level=_level, format=settings.log_format)
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
langchain_agent: Optional[Any] = None


class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI 응답")


@app.on_event("startup")
async def startup() -> None:
    global vllm_client, mcp_tools, langchain_agent
    config = get_vllm_config()
    vllm_client = VLLMClient(
        config["base_url"],
        config["model"],
        max_tokens=config.get("max_tokens", 1000),
        temperature=config.get("temperature", 0.7),
        timeout=config.get("timeout", 60),
    )
    mcp_tools = MCPTools()
    # Initialize LangChain agent backed by vLLM's OpenAI-compatible API
    if _LANGCHAIN_AVAILABLE:
        # vLLM exposes OpenAI-compatible API, so set base_url and dummy key
        llm = ChatOpenAI(
            api_key="unused",
            base_url=f"{config['base_url']}/v1",
            model=config["model"],
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 1000),
            timeout=config.get("timeout", 60),
        )

        # Wrap MCPTools methods as LangChain tools
        @tool("get_current_time")
        async def lc_get_current_time(timezone: str = "Asia/Seoul") -> str:
            """Get current time for a timezone (default Asia/Seoul)."""
            return await mcp_tools.get_current_time(timezone=timezone)

        @tool("fetch_url")
        async def lc_fetch_url(url: str) -> str:
            """Fetch the text content of a URL (first 1000 chars)."""
            return await mcp_tools.fetch_url(url=url)

        tools = [lc_get_current_time, lc_fetch_url]

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT + " Use tools when helpful. Answer concisely.\n\nYou have access to the following tools:\n{tools}\n\nUse the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [{tool_names}]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final answer to the original input question"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        langchain_agent = AgentExecutor(
            agent=create_react_agent(llm=llm, tools=tools, prompt=prompt),
            tools=tools,
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=6,
        )


@app.on_event("shutdown")
async def shutdown() -> None:
    if vllm_client:
        await vllm_client.close()
    if mcp_tools:
        await mcp_tools.close()
    # LangChain agent has no explicit close


SYSTEM_PROMPT = (
    "You are a helpful assistant with tool-use abilities. "
    "When the user asks for factual, current, or external information, prefer using tools. "
    "For time queries, call get_current_time with an appropriate timezone. "
    "Always return concise answers. "
    "너의 이름은 갤럭시이고, 사용자의 의도에 따라 친절하게 답변을 한다."
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
    
    # For gpt-oss models, use harmony format without tools parameter
    if "gpt-oss" in vllm_client.model.lower():
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT + " You have access to tools like get_current_time and fetch_url. Use them when needed by describing your actions in natural language."},
            {"role": "user", "content": request.message},
        ]
        try:
            # Call without tools parameter for gpt-oss models
            response = await vllm_client.chat(messages)
            msg = response["choices"][0]["message"]
            return ChatResponse(response=msg.get("content", ""))
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise HTTPException(status_code=500, detail="Chat processing failed")
    
    # Standard OpenAI function calling for other models
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


@app.post("/api/agent_chat", response_model=ChatResponse)
async def agent_chat(request: ChatRequest) -> ChatResponse:
    """LangChain 기반 에이전트와 채팅 (ReAct + Tools)"""
    if not _LANGCHAIN_AVAILABLE:
        raise HTTPException(status_code=500, detail="LangChain not installed")
    if not langchain_agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    try:
        # AgentExecutor supports async invoke via .ainvoke
        result = await langchain_agent.ainvoke({"input": request.message})
        # result may be dict with 'output'
        output = result.get("output") if isinstance(result, dict) else str(result)
        return ChatResponse(response=output or "")
    except Exception as e:
        logger.error(f"Agent chat error: {e}")
        raise HTTPException(status_code=500, detail="Agent chat failed")


@app.post("/api/gpt_oss_chat", response_model=ChatResponse)
async def gpt_oss_chat(request: ChatRequest) -> ChatResponse:
    """gpt-oss 모델 전용 채팅 (내장 도구 사용)"""
    if not vllm_client:
        raise HTTPException(status_code=500, detail="Server not initialized")
    
    # gpt-oss harmony format - simple messages without tools parameter
    messages = [
        {"role": "system", "content": "You are Galaxy, a helpful assistant with built-in tool capabilities. When users ask for current information, time, or web content, use your built-in tools naturally. 너의 이름은 갤럭시이고, 사용자의 의도에 따라 친절하게 답변을 한다."},
        {"role": "user", "content": request.message}
    ]
    
    try:
        # Call vLLM without tools parameter for gpt-oss
        response = await vllm_client.chat(messages)
        msg = response["choices"][0]["message"]
        return ChatResponse(response=msg.get("content", ""))
    except Exception as e:
        logger.error(f"GPT-OSS chat error: {e}")
        raise HTTPException(status_code=500, detail="GPT-OSS chat failed")


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