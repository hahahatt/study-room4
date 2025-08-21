# --- add project root to sys.path (must be first) ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]  # .../study-room4
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ----------------------------------------------------

import streamlit as st

st.set_page_config(page_title="내부자 보안 잠금 - 대시보드", layout="wide", page_icon="🔒")

# 홈페이지 로고
from backend.ui import show_logo
show_logo(max_width=400, pad=2, compact=True)  # 크키, 여백 조절 가능

# ----- 접근 가드: 로그인 필수 -----
if not st.session_state.get("authenticated"):
    st.error("로그인이 필요합니다.")
    try:
        st.page_link("app.py", label="⬅️ 로그인 페이지로 이동")
    except Exception:
        pass
    st.stop()

# ----- 상단 바 -----
top = st.columns([6, 2])
with top[0]:
    st.title("내부자 보안 잠금")
with top[1]:
    st.caption(f"👤 {st.session_state.get('username','')}")
    if st.button("로그아웃", use_container_width=True):
        st.session_state.clear()
        try:
            st.switch_page("app.py")
        except Exception:
            st.success("로그아웃 되었습니다. 로그인 페이지로 돌아가세요.")
            st.page_link("app.py", label="⬅️ 로그인 페이지")
        st.stop()

# ----- 본문: 대시보드 위젯 -----
col1, col2, col3, col4 = st.columns(4)
col1.metric("오늘 검사", 0)
col2.metric("차단 건", 0)
col3.metric("승인 대기", 0)
col4.metric("평균 처리시간", "—")

st.info("왼쪽 사이드바에서 [파일 검사] 또는 [이메일 검사]를 선택하세요.")