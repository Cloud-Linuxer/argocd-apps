import requests
from typing import Dict


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def chat(self, message: str) -> Dict:
        """채팅 메시지 전송"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"message": message},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
