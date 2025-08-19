import os
import streamlit as st
import pandas as pd
from utils import read_log

st.set_page_config(page_title="로그 대시보드", layout="wide", page_icon="📈")
st.markdown("# 📈 로그 대시보드")

df = read_log()
if df.empty:
    st.caption("아직 로그가 없습니다.")
    st.stop()

st.subheader("최근 100건")
st.dataframe(df.tail(100), use_container_width=True)

st.subheader("일자별 탐지 건수")
if "ts" in df and not df["ts"].isna().all():
    df["day"] = df["ts"].dt.date
    agg = df.groupby("day")[["주민등록번호","이메일","전화번호"]].sum(numeric_only=True).fillna(0)
    st.bar_chart(agg)
else:
    st.caption("날짜 정보를 파싱할 수 없습니다.")

# CSV 다운로드
st.download_button(
    "🔽 전체 로그 CSV 다운로드",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="audit_log.csv",
    mime="text/csv"
)