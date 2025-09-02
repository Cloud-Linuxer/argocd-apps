import streamlit as st
import os
from api_client import BackendClient

# 페이지 설정
st.set_page_config(
    page_title="VLLM Agent Chat",
    page_icon="🤖",
    layout="wide"
)

# 백엔드 URL 설정
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend-service")
client = BackendClient(BACKEND_URL)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 사이드바
with st.sidebar:
    st.title("🤖 VLLM Agent")
    
    # 서비스 상태
    if client.health_check():
        st.success("✅ 백엔드 연결됨")
        info = client.get_info()
        if "error" not in info:
            st.info(f"모델: {info.get('vllm_model', 'N/A')}")
            st.info(f"환경: {info.get('environment', 'N/A')}")
    else:
        st.error("❌ 백엔드 연결 실패")
    
    st.divider()
    
    # 대화 기록 관리
    if st.button("🗑️ 대화 기록 초기화"):
        if client.clear_conversation():
            st.session_state.messages = []
            st.success("대화 기록이 초기화되었습니다")
            st.rerun()
        else:
            st.error("초기화 실패")

# 메인 영역
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
        with st.spinner("응답 생성 중..."):
            response = client.chat(prompt)
            
            if "error" in response:
                st.error(f"오류: {response['error']}")
                assistant_response = "죄송합니다. 오류가 발생했습니다."
            else:
                assistant_response = response.get("response", "응답을 받지 못했습니다.")
            
            st.markdown(assistant_response)
    
    # 어시스턴트 메시지 추가
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})

# 페이지 하단 정보
st.divider()
st.caption(f"백엔드: {BACKEND_URL}")
