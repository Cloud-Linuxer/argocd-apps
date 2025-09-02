import streamlit as st
import os
from api_client import BackendClient

st.set_page_config(page_title="🌌 Galaxy Chat", page_icon="🌌", layout="wide")

# 우주 느낌의 배경과 읽기 쉬운 채팅 스타일 적용
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 50% 50%, #1a2a6c, #000000);
        color: #ffffff;
    }
    div[data-testid="stChatMessage"] {
        background-color: rgba(0, 0, 0, 0.6);
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 백엔드 URL 설정
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend-service")
client = BackendClient(BACKEND_URL)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("💬 VLLM Agent Chat")

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력
if prompt := st.chat_input("메시지를 입력하세요..."):
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 어시스턴트 응답
    with st.chat_message("assistant"):
        response = client.chat(prompt)
        
        if "error" in response:
            assistant_response = "오류가 발생했습니다."
        else:
            assistant_response = response.get("response", "응답을 받지 못했습니다.")
        
        st.markdown(assistant_response)
    
    # 어시스턴트 메시지 추가
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
