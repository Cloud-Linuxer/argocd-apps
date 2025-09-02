import httpx
import logging
from typing import Dict, Any, List, Optional

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

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
            # Only include tool_choice when explicitly provided
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice

        logger.debug("vLLM payload: %s", {k: (v if k != "messages" else [m.get("role") for m in v]) for k, v in payload.items()})

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            body = exc.response.text if exc.response is not None else ""
            logger.error("vLLM HTTP error %s: %s", status if status is not None else "?", body)
            # Fallback: retry without tools if server errors and tools were included
            if status and status >= 500 and "tools" in payload:
                logger.warning("Retrying without tools due to server error %s", status)
                fallback_payload = {
                    k: v for k, v in payload.items() if k not in {"tools", "tool_choice"}
                }
                logger.debug("vLLM fallback payload: %s", {k: (v if k != "messages" else [m.get("role") for m in v]) for k, v in fallback_payload.items()})
                response = await self.client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=fallback_payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
            else:
                raise
        data = response.json()
        logger.debug("vLLM response keys: %s", list(data.keys()))
        return data

    async def close(self) -> None:
        await self.client.aclose()