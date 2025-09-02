import requests
import streamlit as st
from typing import Dict, List, Optional


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    def chat(self, message: str) -> Dict:
        """채팅 메시지 전송"""
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"message": message},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_conversation(self) -> List[Dict]:
        """대화 기록 조회"""
        try:
            response = requests.get(f"{self.base_url}/api/conversation")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return []
    
    def clear_conversation(self) -> bool:
        """대화 기록 초기화"""
        try:
            response = requests.delete(f"{self.base_url}/api/conversation")
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
    
    def get_info(self) -> Dict:
        """서비스 정보 조회"""
        try:
            response = requests.get(f"{self.base_url}/api/info")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return {"status": "error"}
    
    def health_check(self) -> bool:
        """헬스체크"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
