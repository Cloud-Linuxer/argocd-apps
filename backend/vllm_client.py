import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VLLMClient:
    """VLLM API 클라이언트"""

    async def chat(self, message: str) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": message}],
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
