import re
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)


class MCPTools:
    """Minimal MCP tools for time and URL fetching"""

    def __init__(self) -> None:
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self.http_client.aclose()

    async def get_current_time(self, timezone: str = "Asia/Seoul") -> str:
        """Return current time for a timezone (default Asia/Seoul)"""
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("Asia/Seoul")
        now = datetime.now(tz)
        return now.strftime("%Y-%m-%d %H:%M:%S %Z")

    async def fetch_url(self, url: str) -> str:
        """Fetch URL content and return plain text"""
        try:
            resp = await self.http_client.get(url)
            resp.raise_for_status()
            text = resp.text
            # crude HTML tag removal
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text[:1000]
        except Exception as e:
            logger.error(f"fetch_url error: {e}")
            return f"URL fetch failed: {e}"

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return tool schemas for VLLM function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get current time for a timezone (default Asia/Seoul).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "Timezone name, e.g., Asia/Seoul"
                            }
                        },
                        # omit empty required to avoid schema validation quirks
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_url",
                    "description": "Fetch the text content of a URL (first 1000 chars).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to retrieve"
                            }
                        },
                        "required": ["url"]
                    },
                },
            },
        ]
