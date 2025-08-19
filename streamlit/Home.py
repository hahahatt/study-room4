import streamlit as st

st.set_page_config(page_title="내부자 보안 잠금", layout="wide", page_icon="🔒")
st.title("내부자 보안 잠금")

col1, col2, col3, col4 = st.columns(4)
col1.metric("오늘 검사", 0)
col2.metric("차단 건", 0)
col3.metric("승인 대기", 0)
col4.metric("평균 처리시간", "—")

st.info("왼쪽 사이드바에서 [파일 검사] 또는 [이메일 검사]를 선택하세요.")
