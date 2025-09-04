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
        
        # If tools are requested, use chat completions
        if tools:
            payload: Dict[str, Any] = {
                "model": self.model,
                "messages": filtered_messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "tools": tools,
                "tool_choice": tool_choice if tool_choice is not None else "auto"
            }
            
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
            except Exception as e:
                logger.error("Chat completions failed: %s", e)
                raise
        
        # For simple chat without tools, use completions endpoint as fallback
        # Convert messages to a single prompt
        prompt_parts = []
        for msg in filtered_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        prompt = "\n".join(prompt_parts) + "\nAssistant:"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        logger.debug("vLLM completions payload: %s", payload)

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            
            # Convert completions response to chat completions format
            if "choices" in data and len(data["choices"]) > 0:
                completion_text = data["choices"][0].get("text", "")
                # Convert to chat completions format
                chat_response = {
                    "id": data.get("id", ""),
                    "object": "chat.completion",
                    "created": data.get("created", 0),
                    "model": data.get("model", self.model),
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": completion_text.strip(),
                            "refusal": None,
                            "annotations": None,
                            "audio": None,
                            "function_call": None,
                            "tool_calls": [],
                            "reasoning_content": ""
                        },
                        "logprobs": data["choices"][0].get("logprobs"),
                        "finish_reason": data["choices"][0].get("finish_reason"),
                        "stop_reason": data["choices"][0].get("stop_reason")
                    }],
                    "usage": data.get("usage", {}),
                    "service_tier": data.get("service_tier"),
                    "system_fingerprint": data.get("system_fingerprint")
                }
                logger.debug("Converted completions to chat format")
                return chat_response
            
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            body = exc.response.text if exc.response is not None else ""
            logger.error("vLLM HTTP error %s: %s", status if status is not None else "?", body)
            raise RuntimeError(f"vLLM server returned HTTP {status}: {body}") from exc
        except httpx.RequestError as exc:
            logger.error("vLLM request failed: %s", exc)
            raise RuntimeError(f"Failed to call vLLM server: {exc}") from exc
        
        # Fallback empty response
        return {
            "choices": [{"message": {"role": "assistant", "content": "응답을 생성할 수 없습니다."}}]
        }

    async def close(self) -> None:
        await self.client.aclose()
