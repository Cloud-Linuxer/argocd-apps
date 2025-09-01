"""
MCP (Model Context Protocol) 호환 도구들
다양한 외부 시스템과의 통합을 위한 도구 모음
"""

import json
import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import httpx
import os
from pathlib import Path

from agent import Tool, ToolType
from config import get_settings, get_k8s_config, get_vllm_config

logger = logging.getLogger(__name__)


class MCPTools:
    """MCP 호환 도구 컬렉션"""
    
    def __init__(self):
        self.settings = get_settings()
        self.k8s_config = get_k8s_config()
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
    
    # 파일 시스템 도구들
    
    async def read_file(self, file_path: str) -> str:
        """파일 내용 읽기"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"파일을 찾을 수 없습니다: {file_path}"
            
            if path.is_dir():
                return f"디렉토리입니다: {file_path}"
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return f"파일 내용 ({file_path}):\n{content}"
        
        except Exception as e:
            logger.error(f"파일 읽기 오류: {e}")
            return f"파일 읽기 실패: {str(e)}"
    
    async def write_file(self, file_path: str, content: str) -> str:
        """파일에 내용 쓰기"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"파일 작성 완료: {file_path}"
        
        except Exception as e:
            logger.error(f"파일 쓰기 오류: {e}")
            return f"파일 쓰기 실패: {str(e)}"
    
    async def list_directory(self, directory_path: str = ".") -> str:
        """디렉토리 내용 나열"""
        try:
            path = Path(directory_path)
            if not path.exists():
                return f"디렉토리를 찾을 수 없습니다: {directory_path}"
            
            if not path.is_dir():
                return f"파일입니다 (디렉토리 아님): {directory_path}"
            
            items = []
            for item in path.iterdir():
                item_type = "DIR" if item.is_dir() else "FILE"
                items.append(f"{item_type}: {item.name}")
            
            return f"디렉토리 내용 ({directory_path}):\n" + "\n".join(items)
        
        except Exception as e:
            logger.error(f"디렉토리 나열 오류: {e}")
            return f"디렉토리 나열 실패: {str(e)}"
    
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
    
    # Kubernetes 클러스터 도구들
    
    async def kubectl_get_pods(self, namespace: str = "default") -> str:
        """Kubernetes 파드 목록 조회"""
        try:
            # SSH를 통해 kubectl 명령 실행
            cmd = f"sshpass -p '{self.k8s_config['password']}' ssh -o StrictHostKeyChecking=no {self.k8s_config['user']}@{self.k8s_config['host']} 'kubectl get pods -n {namespace}'"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return f"Kubernetes 파드 목록 (네임스페이스: {namespace}):\n{stdout.decode()}"
            else:
                return f"kubectl 명령 실패: {stderr.decode()}"
        
        except Exception as e:
            logger.error(f"kubectl 실행 오류: {e}")
            return f"kubectl 실행 실패: {str(e)}"
    
    async def kubectl_get_services(self, namespace: str = "default") -> str:
        """Kubernetes 서비스 목록 조회"""
        try:
            cmd = f"sshpass -p '{self.k8s_config['password']}' ssh -o StrictHostKeyChecking=no {self.k8s_config['user']}@{self.k8s_config['host']} 'kubectl get svc -n {namespace}'"
            
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return f"Kubernetes 서비스 목록 (네임스페이스: {namespace}):\n{stdout.decode()}"
            else:
                return f"kubectl 명령 실패: {stderr.decode()}"
        
        except Exception as e:
            logger.error(f"kubectl 실행 오류: {e}")
            return f"kubectl 실행 실패: {str(e)}"
    
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
        """수학 계산 수행"""
        try:
            # 안전한 계산을 위해 eval 대신 제한된 연산만 허용
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return "허용되지 않는 문자가 포함되어 있습니다."
            
            result = eval(expression)
            return f"계산 결과: {expression} = {result}"
        
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
            
            # 파일 시스템 도구
            Tool(
                name="read_file",
                description="파일의 내용을 읽습니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "읽을 파일의 경로"
                        }
                    },
                    "required": ["file_path"]
                },
                function=self.read_file,
                tool_type=ToolType.MCP_TOOL
            ),
            
            Tool(
                name="write_file",
                description="파일에 내용을 작성합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "작성할 파일의 경로"
                        },
                        "content": {
                            "type": "string",
                            "description": "파일에 작성할 내용"
                        }
                    },
                    "required": ["file_path", "content"]
                },
                function=self.write_file,
                tool_type=ToolType.MCP_TOOL
            ),
            
            Tool(
                name="list_directory",
                description="디렉토리의 내용을 나열합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "나열할 디렉토리 경로 (기본값: 현재 디렉토리)"
                        }
                    },
                    "required": []
                },
                function=self.list_directory,
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
            
            # Kubernetes 도구
            Tool(
                name="kubectl_get_pods",
                description="Kubernetes 파드 목록을 조회합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "네임스페이스 (기본값: default)"
                        }
                    },
                    "required": []
                },
                function=self.kubectl_get_pods,
                tool_type=ToolType.MCP_TOOL
            ),
            
            Tool(
                name="kubectl_get_services",
                description="Kubernetes 서비스 목록을 조회합니다.",
                parameters={
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "네임스페이스 (기본값: default)"
                        }
                    },
                    "required": []
                },
                function=self.kubectl_get_services,
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
