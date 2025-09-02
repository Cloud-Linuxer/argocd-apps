import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VLLMClient:
    """VLLM API 클라이언트"""

    def __init__(
        self,
        base_url: str,
        model: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = httpx.AsyncClient(timeout=timeout)

    async def chat(self, message: str) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        response = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def close(self) -> None:
        await self.client.aclose()
