# streamlit/pages/2_이메일 검사.py
import sys
from pathlib import Path
import streamlit as st

# 1) 프로젝트 루트 경로를 sys.path에 추가  (…/streamlit/pages/2_이메일 검사.py → 상위 2단계가 project-root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# 2) 우리가 우선시하는 새 이메일 로직을 "backend.email" 경로로 임포트
from backend.email.gmail_auth import authenticate_user
from backend.email.email_sender import send_email_ui


# 홈페이지 로고
from backend.ui import show_logo
show_logo(max_width=400, pad=2, compact=True)  # 크키, 여백 조절 가능

st.set_page_config(page_title="이메일 검사 · InsiderLock", layout="wide")
st.title("📧 이메일 검사 및 발송")


# ----- 접근 가드: 로그인 필수 -----
if not st.session_state.get("authenticated"):
    st.error("로그인이 필요합니다.")
    try:
        st.page_link("app.py", label="⬅️ 로그인 페이지로 이동")
    except Exception:
        pass
    st.stop()


# Gmail 인증
if "gmail_creds" not in st.session_state:
    st.session_state.gmail_creds = None

if st.session_state.gmail_creds is None:
    st.info("먼저 Gmail 인증이 필요합니다. 아래 버튼을 눌러 인증을 진행하세요.")
    if st.button("🔐 Gmail 인증하기", use_container_width=True):
        try:
            creds = authenticate_user()
            st.session_state.gmail_creds = creds
            st.success("인증 완료! 아래에서 메일 검사를 진행하세요.")
        except Exception as e:
            st.error(f"❌ 인증 실패: {e}")
else:
    st.success("Gmail 인증 상태: 사용 가능")

# 검사/전송 UI (새 로직 우선 사용)
if st.session_state.gmail_creds:
    send_email_ui(st.session_state.gmail_creds)
