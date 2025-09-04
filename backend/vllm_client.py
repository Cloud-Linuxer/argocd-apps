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
        # Filter out messages with None content
        filtered_messages = []
        for msg in messages:
            if msg.get("content") is None:
                msg = {**msg, "content": ""}
            filtered_messages.append(msg)
        
        # 일반 질문: /v1/chat/completions (라벨 텍스트 금지)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": filtered_messages,
            "max_tokens": self.max_tokens,
            "temperature": min(self.temperature, 0.3),  # gpt-oss에 최적화
            "frequency_penalty": 0.2,  # 반복 방지
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice if tool_choice is not None else "auto"
        
        logger.debug("vLLM chat payload: %s", {k: (v if k != "messages" else [m.get("role") for m in v]) for k, v in payload.items()})

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            logger.debug("vLLM response keys: %s", list(data.keys()))
            return data
            
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            body = exc.response.text if exc.response is not None else ""
            logger.error("vLLM HTTP error %s: %s", status if status is not None else "?", body)
            raise RuntimeError(f"vLLM server returned HTTP {status}: {body}") from exc
        except httpx.RequestError as exc:
            logger.error("vLLM request failed: %s", exc)
            raise RuntimeError(f"Failed to call vLLM server: {exc}") from exc

    async def close(self) -> None:
        await self.client.aclose()
