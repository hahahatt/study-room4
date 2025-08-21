# --- add project root to sys.path ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ------------------------------------

import streamlit as st
import pandas as pd
from datetime import date
from backend.log import (
    list_email_logs, build_filter, PII_KEYS,
    list_file_logs, build_file_filter
)


# 홈페이지 로고
from backend.ui import show_logo
show_logo(max_width=400, pad=2, compact=True)  # 크키, 여백 조절 가능

st.set_page_config(page_title="로그 대시보드", layout="wide")
st.title("이메일/파일 로그 대시보드")

# 세션 페이징
st.session_state.setdefault("email_page", 1)
st.session_state.setdefault("file_page", 1)
st.session_state.setdefault("page_size", 20)

# ── 메인 필터
st.subheader("필터")
fc1, fc2, fc3, fc4, fc5 = st.columns([2, 1.2, 1.2, 1.2, 1.2])
with fc1: keyword = st.text_input("키워드 (제목/본문/파일명)")
with fc2: user_q = st.text_input("사용자")
with fc3: to_q = st.text_input("받는 사람(이메일 로그 전용)")
with fc4: masked_opt = st.selectbox("마스킹 여부(이메일 로그 전용)", ["전체", "마스킹", "원본"], index=0)
with fc5:
    page_size = st.selectbox("페이지 크기", [10, 20, 50, 100], index=1)
    st.session_state.page_size = page_size

dc1, dc2, dc3 = st.columns([1,1,1])
with dc1: df_str = st.date_input("시작일", value=None, key="from_date")
with dc2: dt_str = st.date_input("종료일", value=None, key="to_date")
with dc3:
    if st.button("적용 / 새로고침"):
        st.session_state.email_page = 1
        st.session_state.file_page = 1

masked = {"전체": None, "마스킹": True, "원본": False}[masked_opt]
date_from = df_str.isoformat() if isinstance(df_str, date) else None
date_to   = dt_str.isoformat() if isinstance(dt_str, date) else None

email_filters = build_filter(
    keyword=keyword or None, masked=masked, user=user_q or None, to=to_q or None,
    date_from=date_from, date_to=date_to
)
file_filters = build_file_filter(
    keyword=keyword or None, user=user_q or None,
    date_from=date_from, date_to=date_to
)

tab1, tab2 = st.tabs(["이메일 로그", "파일 로그"])

# ── 이메일 로그 탭
with tab1:
    page = st.session_state.email_page
    items, total = list_email_logs(page=page, page_size=st.session_state.page_size, filters=email_filters)

    k1, k2, k3 = st.columns(3)
    k1.metric("총 이메일 로그", f"{total:,}")
    k2.metric("현재 페이지", f"{page}")
    if items:
        masked_cnt = sum(1 for x in items if x.get("masked") == "O")
        k3.metric("이 페이지 - 마스킹 전송", f"{masked_cnt}/{len(items)}")
    else:
        k3.metric("이 페이지 - 마스킹 전송", "0/0")

    def to_email_rows(rows):
        out = []
        for r in rows:
            row = {
                "보낸 시각": r.get("sent_at"),
                "마스킹": r.get("masked"),                  # ✅ O/X
                "사용자": r.get("user_display"),            # ✅ 사용자 이름
                "받는 사람": r.get("to"),
                "제목": r.get("subject"),
                "첨부(개수)": f"{len(r.get('attachment_names', []))}",
                "첨부 파일들": ", ".join(r.get("attachment_names", []))[:200],
            }
            for k in PII_KEYS:
                row[k] = r.get(f"scan_{k}", 0)
            out.append(row)
        return out

    df_email = pd.DataFrame(to_email_rows(items))
    st.subheader("이메일 로그 목록")
    if df_email.empty:
        st.info("데이터가 없습니다. 필터를 조정해 보세요.")
    else:
        st.dataframe(df_email, use_container_width=True, hide_index=True)
        st.download_button("CSV 다운로드(이메일)", data=df_email.to_csv(index=False), file_name="email_logs.csv", mime="text/csv")

    prev_col, page_col, next_col = st.columns([1,2,1])
    with prev_col:
        if st.button("⬅ 이전(이메일)", disabled=(page <= 1)):
            st.session_state.email_page = max(1, page - 1)
    with page_col:
        last_page = max(1, (total + st.session_state.page_size - 1) // st.session_state.page_size)
        st.write(f"페이지 {page} / {last_page}")
    with next_col:
        if st.button("다음 ➡(이메일)", disabled=(page >= last_page)):
            st.session_state.email_page = min(last_page, page + 1)

# ── 파일 로그 탭
with tab2:
    page = st.session_state.file_page
    items, total = list_file_logs(page=page, page_size=st.session_state.page_size, filters=file_filters)

    k1, k2 = st.columns(2)
    k1.metric("총 파일 로그", f"{total:,}")
    k2.metric("현재 페이지", f"{page}")

    def to_file_rows(rows):
        out = []
        for r in rows:
            row = {
                "업로드 시각": r.get("uploaded_at"),
                "사용자": r.get("user_display"),           # 
                "파일명": r.get("filename"),
                "크기": r.get("size"),
                "콘텐츠 유형": r.get("content_type"),
            }
            for k in PII_KEYS:
                row[k] = r.get(f"scan_{k}", 0)
            out.append(row)
        return out

    df_file = pd.DataFrame(to_file_rows(items))
    st.subheader("파일 로그 목록")
    if df_file.empty:
        st.info("데이터가 없습니다. 필터를 조정해 보세요.")
    else:
        st.dataframe(df_file, use_container_width=True, hide_index=True)
        st.download_button("CSV 다운로드(파일)", data=df_file.to_csv(index=False), file_name="file_logs.csv", mime="text/csv")

    prev_col, page_col, next_col = st.columns([1,2,1])
    with prev_col:
        if st.button("⬅ 이전(파일)", disabled=(page <= 1)):
            st.session_state.file_page = max(1, page - 1)
    with page_col:
        last_page = max(1, (total + st.session_state.page_size - 1) // st.session_state.page_size)
        st.write(f"페이지 {page} / {last_page}")
    with next_col:
        if st.button("다음 ➡(파일)", disabled=(page >= last_page)):
            st.session_state.file_page = min(last_page, page + 1)
