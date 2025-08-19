import os
import streamlit as st
import pandas as pd
from utils import read_log, get_policies
from auth import init_auth_state, login_box_in_sidebar, render_login_form_if_needed

ICON = os.path.join(os.path.dirname(__file__), "icon.png")
st.set_page_config(page_title="내부자 보안 잠금", layout="wide", page_icon=ICON if os.path.exists(ICON) else "🔒")

init_auth_state()          # ← 세션 초기화
login_box_in_sidebar()     # ← 사이드바 하단에 로그인 버튼 그리기

# 페이지 헤더/메트릭 등 기존 내용…
render_login_form_if_needed()  # ← 로그인 버튼 누르면 메인에 폼 띄우기
# 헤더
col_icon, col_title = st.columns([1, 8])
with col_icon:
    if os.path.exists(ICON):
        st.image(ICON, width=44)
with col_title:
    st.markdown("# 🔒 내부자 보안 잠금")

st.info("왼쪽 사이드바에서 [파일 검사] 또는 [이메일 검사]를 선택하세요.")

# 메트릭
df = read_log()
rrn_total = int(df["주민등록번호"].sum()) if "주민등록번호" in df else 0
email_total = int(df["이메일"].sum()) if "이메일" in df else 0
phone_total = int(df["전화번호"].sum()) if "전화번호" in df else 0
today_count = len(df[df["ts"].dt.date == pd.Timestamp.today().date()]) if not df.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("오늘 검사", today_count)
m2.metric("총 RRN 탐지", rrn_total)
m3.metric("총 이메일 탐지", email_total)
m4.metric("총 전화번호 탐지", phone_total)

# 정책 요약
pol = get_policies(st.session_state)
with st.sidebar:
    st.header("정책 요약")
    st.caption(f"주민등록번호 포함 시 차단: **{pol['block_if_rrn']}**")
    st.caption(f"이메일 포함 시 경고: **{pol['warn_if_email']}**")
    st.caption(f"총 업로드 용량 제한: **{pol['max_total_mb']} MB**")
    st.caption(f"파일 최대 개수: **{pol['max_files']}개**")

# 최근 로그 미리보기
st.subheader("최근 검사 로그")
if df.empty:
    st.caption("아직 로그가 없습니다.")
else:
    st.dataframe(df.tail(15), use_container_width=True)
