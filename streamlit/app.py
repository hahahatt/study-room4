# --- add project root to sys.path (robust) ---
import sys
from pathlib import Path

_here = Path(__file__).resolve()
# backend 폴더를 포함하는 상위 폴더를 자동 탐색
for p in [_here, *_here.parents]:
    if (p / "backend").exists():
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
        break
else:
    # 디버깅용: 실패 시 현재 경로 출력
    print("[PathError] 'backend' 폴더를 찾지 못했습니다. 현재:", _here)
# ----------------------------------------------------


import os
import streamlit as st
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

st.set_page_config(page_title="내부자 보안 잠금 - 로그인", layout="wide", page_icon="🔒")

# ----- .env 로드 -----
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("MONGO_DB", "insiderlock")
USERS_COL = os.getenv("MONGO_USERS_COLLECTION", "users")

# ----- DB 연결(캐시) -----
@st.cache_resource
def get_users_col():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    col = db[USERS_COL]
    try:
        col.create_index([("username", ASCENDING)], unique=True)
    except Exception:
        pass
    return col

users_col = get_users_col()

# ----- 인증 유틸(평문 저장 기준) -----
def verify_user_plain(username: str, password: str) -> bool:
    doc = users_col.find_one({"username": username})
    return bool(doc and doc.get("password") == password)

# ----- 이미 로그인 되어 있다면 대시보드로 -----
if st.session_state.get("authenticated"):
    # 최신 Streamlit이면 switch_page 가능
    try:
        st.switch_page("pages/01_Dashboard.py")
    except Exception:
        st.success("이미 로그인됨. 대시보드로 이동하세요.")
        st.page_link("pages/0_Home.py", label="➡️ 대시보드로 이동")
    st.stop()


# 홈페이지 로고
from backend.ui import show_logo
show_logo(max_width=400, pad=2, compact=True)  # 크키, 여백 조절 가능

# ----- 로그인 폼 -----
st.subheader("로그인")

with st.form("login_form", clear_on_submit=False):
    username = st.text_input("아이디", placeholder="아이디를 입력하세요")
    password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
    ok = st.form_submit_button("로그인")

if ok:
    if verify_user_plain(username, password):
        st.session_state.authenticated = True
        st.session_state.username = username
        st.success("로그인 성공! 대시보드로 이동합니다.")
        # 바로 페이지 전환 시도
        try:
            st.switch_page("pages/0_Home.py")
        except Exception:
            st.page_link("pages/0_Home.py", label="➡️ 대시보드로 이동")
        st.stop()
    else:
        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")