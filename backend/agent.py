"""
VLLM 기반 펑션콜 에이전트 구현
openai/gpt-oss-20b 모델을 사용한 AI 에이전트
"""

import json
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum

import httpx
from pydantic import BaseModel, Field
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """도구 타입 정의"""
    FUNCTION = "function"
    MCP_TOOL = "mcp_tool"
    SYSTEM = "system"


@dataclass
class ToolResult:
    """도구 실행 결과"""
    success: bool
    result: Any
    error: Optional[str] = None
    tool_name: str = ""
    execution_time: float = 0.0


class Tool(BaseModel):
    """에이전트가 사용할 도구 정의"""
    name: str = Field(..., description="도구 이름")
    description: str = Field(..., description="도구 설명")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="도구 파라미터 스키마")
    function: Optional[Callable] = Field(default=None, description="실행할 함수")
    tool_type: ToolType = Field(default=ToolType.FUNCTION, description="도구 타입")
    
    class Config:
        arbitrary_types_allowed = True


class VLLMClient:
    """VLLM API 클라이언트"""
    
    def __init__(self, base_url: str = "http://192.168.0.2:30081", model: str = "openai/gpt-oss-20b"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """채팅 완성 API 호출"""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        
        except httpx.RequestError as e:
            logger.error(f"VLLM API 요청 오류: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"VLLM API HTTP 오류: {e.response.status_code} - {e.response.text}")
            raise
    
    async def get_models(self) -> Dict[str, Any]:
        """사용 가능한 모델 목록 조회"""
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"모델 조회 오류: {e}")
            raise
    
    async def close(self):
        """클라이언트 종료"""
        await self.client.aclose()


class FunctionCallAgent:
    """VLLM 기반 펑션콜 에이전트"""
    
    def __init__(
        self, 
        vllm_client: VLLMClient,
        system_prompt: Optional[str] = None,
        max_iterations: int = 10
    ):
        self.vllm_client = vllm_client
        self.tools: Dict[str, Tool] = {}
        self.conversation_history: List[BaseMessage] = []
        self.max_iterations = max_iterations
        
        # 기본 시스템 프롬프트
        default_system_prompt = """
당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 답하고 요청된 작업을 수행하기 위해 제공된 도구들을 사용할 수 있습니다.

도구를 사용할 때는 다음 형식을 따르세요:
```json
{
  "tool_call": {
    "name": "도구_이름",
    "parameters": {
      "매개변수명": "값"
    }
  }
}
```

도구 사용이 완료되면 결과를 바탕으로 사용자에게 명확하고 도움이 되는 답변을 제공하세요.
"""
        
        self.system_prompt = system_prompt or default_system_prompt
        self.conversation_history.append(SystemMessage(content=self.system_prompt))
    
    def add_tool(self, tool: Tool):
        """도구 추가"""
        self.tools[tool.name] = tool
        logger.info(f"도구 '{tool.name}' 추가됨")
    
    def remove_tool(self, tool_name: str):
        """도구 제거"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"도구 '{tool_name}' 제거됨")
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """OpenAI 함수 호출 형식으로 도구 스키마 반환"""
        tools_schema = []
        for tool in self.tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            tools_schema.append(schema)
        return tools_schema
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """도구 실행"""
        import time
        start_time = time.time()
        
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                result=None,
                error=f"도구 '{tool_name}'를 찾을 수 없습니다.",
                tool_name=tool_name,
                execution_time=time.time() - start_time
            )
        
        tool = self.tools[tool_name]
        
        try:
            if tool.function:
                if asyncio.iscoroutinefunction(tool.function):
                    result = await tool.function(**parameters)
                else:
                    result = tool.function(**parameters)
            else:
                result = f"도구 '{tool_name}' 실행됨 (파라미터: {parameters})"
            
            return ToolResult(
                success=True,
                result=result,
                tool_name=tool_name,
                execution_time=time.time() - start_time
            )
        
        except Exception as e:
            logger.error(f"도구 '{tool_name}' 실행 오류: {e}")
            return ToolResult(
                success=False,
                result=None,
                error=str(e),
                tool_name=tool_name,
                execution_time=time.time() - start_time
            )
    
    def _parse_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """AI 응답에서 도구 호출 파싱"""
        try:
            # JSON 코드 블록 찾기
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end != -1:
                    json_str = content[start:end].strip()
                    parsed = json.loads(json_str)
                    if "tool_call" in parsed:
                        return parsed["tool_call"]
            
            # 직접 JSON 파싱 시도
            try:
                parsed = json.loads(content)
                if "tool_call" in parsed:
                    return parsed["tool_call"]
            except:
                pass
            
            return None
        
        except Exception as e:
            logger.error(f"도구 호출 파싱 오류: {e}")
            return None
    
    async def chat(self, user_message: str) -> str:
        """사용자와 채팅"""
        # 사용자 메시지 추가
        self.conversation_history.append(HumanMessage(content=user_message))
        
        iterations = 0
        while iterations < self.max_iterations:
            iterations += 1
            
            # 메시지를 API 형식으로 변환
            messages = []
            for msg in self.conversation_history:
                if isinstance(msg, SystemMessage):
                    messages.append({"role": "system", "content": msg.content})
                elif isinstance(msg, HumanMessage):
                    messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    messages.append({"role": "assistant", "content": msg.content})
            
            # VLLM API 호출
            try:
                response = await self.vllm_client.chat_completion(
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.7,
                    tools=self.get_tools_schema() if self.tools else None
                )
                
                ai_message = response["choices"][0]["message"]["content"]
                
                # 도구 호출 확인
                tool_call = self._parse_tool_call(ai_message)
                
                if tool_call and "name" in tool_call:
                    # 도구 실행
                    tool_name = tool_call["name"]
                    parameters = tool_call.get("parameters", {})
                    
                    logger.info(f"도구 '{tool_name}' 실행 중...")
                    tool_result = await self.execute_tool(tool_name, parameters)
                    
                    # 도구 결과를 대화 기록에 추가
                    self.conversation_history.append(AIMessage(content=ai_message))
                    
                    if tool_result.success:
                        result_message = f"도구 '{tool_name}' 실행 결과: {tool_result.result}"
                    else:
                        result_message = f"도구 '{tool_name}' 실행 실패: {tool_result.error}"
                    
                    self.conversation_history.append(HumanMessage(content=result_message))
                    
                    # 다음 반복으로 계속
                    continue
                
                else:
                    # 도구 호출이 없으면 최종 응답
                    self.conversation_history.append(AIMessage(content=ai_message))
                    return ai_message
            
            except Exception as e:
                logger.error(f"채팅 처리 오류: {e}")
                error_message = f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"
                self.conversation_history.append(AIMessage(content=error_message))
                return error_message
        
        # 최대 반복 횟수 초과
        timeout_message = "죄송합니다. 요청 처리에 너무 많은 단계가 필요합니다."
        self.conversation_history.append(AIMessage(content=timeout_message))
        return timeout_message
    
    def clear_history(self):
        """대화 기록 초기화"""
        self.conversation_history = [SystemMessage(content=self.system_prompt)]
        logger.info("대화 기록이 초기화되었습니다.")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """대화 기록 반환"""
        history = []
        for msg in self.conversation_history:
            if isinstance(msg, SystemMessage):
                history.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                history.append({"role": "assistant", "content": msg.content})
        return history


# 필요한 모듈 import
import asyncio
