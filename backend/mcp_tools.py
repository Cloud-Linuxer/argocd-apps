"""
MCP (Model Context Protocol) 호환 도구들
다양한 외부 시스템과의 통합을 위한 도구 모음
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx

from agent import Tool, ToolType
from config import get_settings, get_vllm_config

logger = logging.getLogger(__name__)


class MCPTools:
    """MCP 호환 도구 컬렉션"""
    
    def __init__(self):
        self.settings = get_settings()
        self.vllm_config = get_vllm_config()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """리소스 정리"""
        await self.http_client.aclose()
    
    # 시스템 정보 도구들
    
    async def get_current_time(self, timezone: str = "Asia/Seoul") -> str:
        """지역별 현재 시간 반환"""
        import pytz
        from datetime import datetime
        
        try:
            tz = pytz.timezone(timezone)
            local_time = datetime.now(tz)
            return f"{timezone}: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        except Exception as e:
            # 기본값으로 서울 시간 반환
            seoul_tz = pytz.timezone("Asia/Seoul")
            seoul_time = datetime.now(seoul_tz)
            return f"Asia/Seoul: {seoul_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
    

    
    # HTTP 요청 도구들
    
    async def http_get(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """HTTP GET 요청"""
        try:
            response = await self.http_client.get(url, headers=headers or {})
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                return json.dumps(response.json(), indent=2, ensure_ascii=False)
            else:
                return response.text
        
        except Exception as e:
            logger.error(f"HTTP GET 오류: {e}")
            return f"HTTP GET 실패: {str(e)}"
    
    async def http_post(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """HTTP POST 요청"""
        try:
            response = await self.http_client.post(
                url, 
                json=data or {}, 
                headers=headers or {}
            )
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                return json.dumps(response.json(), indent=2, ensure_ascii=False)
            else:
                return response.text
        
        except Exception as e:
            logger.error(f"HTTP POST 오류: {e}")
            return f"HTTP POST 실패: {str(e)}"
    

    
    # VLLM API 도구들
    
    async def vllm_get_models(self) -> str:
        """VLLM 모델 목록 조회"""
        try:
            url = f"{self.vllm_config['base_url']}/v1/models"
            response = await self.http_client.get(url)
            response.raise_for_status()
            return json.dumps(response.json(), indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"VLLM 모델 조회 오류: {e}")
            return f"VLLM 모델 조회 실패: {str(e)}"
    
    async def vllm_chat(self, message: str, max_tokens: int = 100) -> str:
        """VLLM 채팅 API 호출"""
        try:
            payload = {
                "model": self.vllm_config['model'],
                "messages": [{"role": "user", "content": message}],
                "max_tokens": max_tokens,
                "temperature": self.vllm_config['temperature']
            }
            
            url = f"{self.vllm_config['base_url']}/v1/chat/completions"
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        except Exception as e:
            logger.error(f"VLLM 채팅 오류: {e}")
            return f"VLLM 채팅 실패: {str(e)}"
    
    # 계산 도구들
    
    async def calculate(self, expression: str) -> str:
        """수학 계산 수행 (기본 연산만)"""
        try:
            # 안전한 계산을 위해 매우 제한적인 연산만 허용
            import re
            
            # 숫자, 기본 연산자, 괄호, 공백만 허용
            if not re.match(r'^[0-9+\-*/.() ]+$', expression):
                return "허용되지 않는 문자가 포함되어 있습니다. 숫자와 +, -, *, /, (), 공백만 사용 가능합니다."
            
            # 보안을 위해 eval 대신 제한적인 계산만 수행
            # 실제 프로덕션에서는 ast.literal_eval 또는 수학 파서 라이브러리 사용 권장
            try:
                result = eval(expression, {"__builtins__": {}}, {})
                return f"계산 결과: {expression} = {result}"
            except:
                return f"계산할 수 없는 수식입니다: {expression}"
        
        except Exception as e:
            logger.error(f"계산 오류: {e}")
            return f"계산 실패: {str(e)}"
    
    # 도구 등록 메서드
    
    def get_all_tools(self) -> List[Tool]:
        """모든 MCP 도구 반환"""
        return [
            # 시스템 도구
            Tool(
                name="get_current_time",
                description="지역별 현재 날짜와 시간을 반환합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "시간대 (예: Asia/Seoul, America/New_York, Europe/London)",
                            "default": "Asia/Seoul"
                        }
                    },
                    "required": []
                },
                function=self.get_current_time,
                tool_type=ToolType.MCP_TOOL
            ),
            
            # HTTP 요청 도구
            Tool(
                name="http_get",
                description="HTTP GET 요청을 수행합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "요청할 URL"
                        },
                        "headers": {
                            "type": "object",
                            "description": "요청 헤더 (선택사항)"
                        }
                    },
                    "required": ["url"]
                },
                function=self.http_get,
                tool_type=ToolType.MCP_TOOL
            ),
            
            Tool(
                name="http_post",
                description="HTTP POST 요청을 수행합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "요청할 URL"
                        },
                        "data": {
                            "type": "object",
                            "description": "POST 데이터 (JSON)"
                        },
                        "headers": {
                            "type": "object",
                            "description": "요청 헤더 (선택사항)"
                        }
                    },
                    "required": ["url"]
                },
                function=self.http_post,
                tool_type=ToolType.MCP_TOOL
            ),
            
            # VLLM 도구
            Tool(
                name="vllm_get_models",
                description="VLLM에서 사용 가능한 모델 목록을 조회합니다.",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                function=self.vllm_get_models,
                tool_type=ToolType.MCP_TOOL
            ),
            
            Tool(
                name="vllm_chat",
                description="VLLM API를 사용해 채팅합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "전송할 메시지"
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "최대 토큰 수 (기본값: 100)"
                        }
                    },
                    "required": ["message"]
                },
                function=self.vllm_chat,
                tool_type=ToolType.MCP_TOOL
            ),
            
            # 계산 도구
            Tool(
                name="calculate",
                description="수학 계산을 수행합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "계산할 수식 (예: 2+2, 10*5, sqrt(16))"
                        }
                    },
                    "required": ["expression"]
                },
                function=self.calculate,
                tool_type=ToolType.MCP_TOOL
            )
        ]
