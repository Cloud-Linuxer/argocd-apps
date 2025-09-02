"""
VLLM 펑션콜 에이전트 설정 관리
환경변수를 통한 설정 값 관리

🚨 보안 경고: 
- 민감한 정보(패스워드, API 키 등)는 절대 기본값으로 설정하지 마세요!
- Field(...) 는 필수 환경변수를 의미합니다.
- 모든 민감한 정보는 환경변수나 .env 파일로 관리하세요.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 환경 설정
    env: str = Field(default="development", description="실행 환경")
    
    # 서버 설정
    host: str = Field(default="0.0.0.0", description="서버 호스트")
    port: int = Field(default=8080, description="서버 포트")
    
    # VLLM 설정 (환경변수 필수!)
    vllm_base_url: str = Field(..., description="VLLM API 기본 URL")
    vllm_model: str = Field(..., description="사용할 VLLM 모델")
    vllm_max_tokens: int = Field(default=1000, description="최대 토큰 수")
    vllm_temperature: float = Field(default=0.7, description="생성 온도")
    vllm_timeout: int = Field(default=60, description="VLLM API 타임아웃 (초)")
    

    
    # 로깅 설정
    log_level: str = Field(default="INFO", description="로그 레벨")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="로그 형식"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
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





