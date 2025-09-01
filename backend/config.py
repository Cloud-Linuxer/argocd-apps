"""
VLLM 펑션콜 에이전트 설정 관리
환경변수를 통한 설정 값 관리
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 환경 설정
    env: str = Field(default="development", description="실행 환경")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", description="서버 호스트")
    port: int = Field(default=8080, description="서버 포트")
    
    # VLLM 설정
    vllm_base_url: str = Field(default="http://192.168.0.2:30081", description="VLLM API 기본 URL")
    vllm_model: str = Field(default="openai/gpt-oss-20b", description="사용할 VLLM 모델")
    vllm_max_tokens: int = Field(default=1000, description="최대 토큰 수")
    vllm_temperature: float = Field(default=0.7, description="생성 온도")
    vllm_timeout: int = Field(default=60, description="VLLM API 타임아웃 (초)")
    
    # Kubernetes 설정
    k8s_host: str = Field(default="192.168.0.2", description="Kubernetes 호스트")
    k8s_user: str = Field(default="root", description="Kubernetes 사용자")
    k8s_password: str = Field(default="Xoghks34!", description="Kubernetes 비밀번호")
    
    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="로그 형식"
    )
    
    # 에이전트 설정
    agent_max_iterations: int = Field(default=10, description="에이전트 최대 반복 횟수")
    agent_timeout: int = Field(default=300, description="에이전트 타임아웃 (초)")
    
    # Redis 설정 (선택사항)
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    redis_enabled: bool = Field(default=False, description="Redis 사용 여부")
    
    # 보안 설정
    api_key_enabled: bool = Field(default=False, description="API 키 인증 사용 여부")
    api_key: Optional[str] = Field(default=None, description="API 키")
    
    # MCP 도구 설정
    mcp_tools_enabled: bool = Field(default=True, description="MCP 도구 사용 여부")
    mcp_security_enabled: bool = Field(default=True, description="MCP 보안 기능 사용 여부")
    mcp_file_access_allowed: bool = Field(default=True, description="파일 시스템 접근 허용")
    mcp_http_requests_allowed: bool = Field(default=True, description="HTTP 요청 허용")
    mcp_kubectl_enabled: bool = Field(default=True, description="kubectl 명령 허용")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # 환경변수 이름 매핑
        fields = {
            "vllm_base_url": {"env": "VLLM_BASE_URL"},
            "vllm_model": {"env": "VLLM_MODEL"},
            "vllm_max_tokens": {"env": "VLLM_MAX_TOKENS"},
            "vllm_temperature": {"env": "VLLM_TEMPERATURE"},
            "vllm_timeout": {"env": "VLLM_TIMEOUT"},
            "k8s_host": {"env": "K8S_HOST"},
            "k8s_user": {"env": "K8S_USER"},
            "k8s_password": {"env": "K8S_PASSWORD"},
            "log_level": {"env": "LOG_LEVEL"},
            "log_format": {"env": "LOG_FORMAT"},
            "agent_max_iterations": {"env": "AGENT_MAX_ITERATIONS"},
            "agent_timeout": {"env": "AGENT_TIMEOUT"},
            "redis_url": {"env": "REDIS_URL"},
            "redis_enabled": {"env": "REDIS_ENABLED"},
            "api_key_enabled": {"env": "API_KEY_ENABLED"},
            "api_key": {"env": "API_KEY"},
            "mcp_tools_enabled": {"env": "MCP_TOOLS_ENABLED"},
            "mcp_security_enabled": {"env": "MCP_SECURITY_ENABLED"},
            "mcp_file_access_allowed": {"env": "MCP_FILE_ACCESS_ALLOWED"},
            "mcp_http_requests_allowed": {"env": "MCP_HTTP_REQUESTS_ALLOWED"},
            "mcp_kubectl_enabled": {"env": "MCP_KUBECTL_ENABLED"},
        }


# 전역 설정 인스턴스
settings = Settings()


def get_settings() -> Settings:
    """설정 인스턴스 반환"""
    return settings


def is_development() -> bool:
    """개발 환경 여부 확인"""
    return settings.env.lower() == "development"


def is_production() -> bool:
    """프로덕션 환경 여부 확인"""
    return settings.env.lower() == "production"


def get_vllm_config() -> dict:
    """VLLM 설정 반환"""
    return {
        "base_url": settings.vllm_base_url,
        "model": settings.vllm_model,
        "max_tokens": settings.vllm_max_tokens,
        "temperature": settings.vllm_temperature,
        "timeout": settings.vllm_timeout
    }


def get_k8s_config() -> dict:
    """Kubernetes 설정 반환"""
    return {
        "host": settings.k8s_host,
        "user": settings.k8s_user,
        "password": settings.k8s_password
    }


def get_agent_config() -> dict:
    """에이전트 설정 반환"""
    return {
        "max_iterations": settings.agent_max_iterations,
        "timeout": settings.agent_timeout
    }


def get_mcp_config() -> dict:
    """MCP 도구 설정 반환"""
    return {
        "enabled": settings.mcp_tools_enabled,
        "security_enabled": settings.mcp_security_enabled,
        "file_access_allowed": settings.mcp_file_access_allowed,
        "http_requests_allowed": settings.mcp_http_requests_allowed,
        "kubectl_enabled": settings.mcp_kubectl_enabled
    }
