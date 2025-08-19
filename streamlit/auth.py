# st_app/auth.py
import streamlit as st

USERS = {"admin": "1234", "user": "abcd"}  # 데모용

def init_auth_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
    if "show_login_form" not in st.session_state:
        st.session_state.show_login_form = False

def login_box_in_sidebar():
    """사이드바 하단: 네모 버튼 '로그인' 1개만"""
    with st.sidebar:
        st.divider()

        # 🔲 네모 버튼 1개만 표시
        if not st.session_state.logged_in:
            # 버튼 자체가 네모 박스니까 별도 박스는 그리지 않습니다.
            if st.button("🔑  로그인", key="btn_login", use_container_width=True):
                st.session_state.show_login_form = True
                st.rerun()
        else:
            st.success(f"🔑 {st.session_state.username} 님 로그인됨")
            if st.button("🚪  로그아웃", key="btn_logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.session_state.show_login_form = False
                st.rerun()

def render_login_form_if_needed(title="🔐 로그인"):
    if st.session_state.get("show_login_form", False) and not st.session_state.logged_in:
        st.subheader(title)
        with st.form("login_form"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            ok = st.form_submit_button("확인")
        if ok:
            if username in USERS and USERS[username] == password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.show_login_form = False
                st.success(f"환영합니다, {username}님!")
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

def require_login():
    if not st.session_state.get("logged_in", False):
        st.session_state.show_login_form = True
        st.info("이 기능을 사용하려면 로그인이 필요합니다. 아래에서 로그인해 주세요.")
        render_login_form_if_needed()
        st.stop()