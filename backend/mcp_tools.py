"""Tool implementations for HTTP requests and time queries."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from zoneinfo import ZoneInfo
import httpx

logger = logging.getLogger(__name__)


class MCPTools:
    """Minimal tools usable by the model."""

    def __init__(self) -> None:
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self.http_client.aclose()

    async def http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        query: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        timeout_s: int = 5,
    ) -> str:
        """Call an HTTP API and return the first 1000 chars of the response."""
        try:
            resp = await self.http_client.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=query,
                json=json,
                timeout=timeout_s,
            )
            resp.raise_for_status()
            return resp.text[:1000]
        except Exception as e:  # pragma: no cover - network dependent
            logger.error("http_request error: %s", e)
            return f"http_request failed: {e}"

    async def time_now(self, timezone: str = "UTC") -> str:
        """Return current time for the given timezone in ISO format."""
        try:
            now = datetime.now(ZoneInfo(timezone))
            return now.isoformat()
        except Exception as e:  # pragma: no cover - tz dependent
            logger.error("time_now error: %s", e)
            return f"time_now failed: {e}"

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return JSON schemas for available tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "http_request",
                    "description": "사내/외부 HTTP API 호출",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                            },
                            "url": {"type": "string", "format": "uri"},
                            "headers": {
                                "type": "object",
                                "additionalProperties": {"type": "string"},
                            },
                            "query": {
                                "type": "object",
                                "additionalProperties": {},
                            },
                            "json": {"type": ["object", "array", "null"]},
                            "timeout_s": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 30,
                            },
                        },
                        "required": ["method", "url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "time_now",
                    "description": "지정된 시간대의 현재 시각을 ISO 형식으로 반환",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "default": "UTC",
                            }
                        },
                        "required": [],
                    },
                },
            },
        ]

