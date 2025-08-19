import streamlit as st
from io import BytesIO
from pathlib import Path
import sys

import re

# ----------------- import 경로 세팅 -----------------
# 현재 파일: <root>/streamlit/pages/1_파일 검사.py
# backend 폴더는 <root>/backend 에 있으므로 부모의 부모를 sys.path에 추가
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.masking import run_masking_pipeline
from backend.file_logger import log_scan


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
    st.title("파일 검사 테스트 페이지")
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

# ----------------- 본문 : 파일 검사  ---------------------------
files = st.file_uploader("파일 업로드", accept_multiple_files=True, type=["txt"])
if not files:
    st.caption("샘플: .txt 파일을 올려보세요 (주민번호, 이메일 탐지 예시).")
    st.stop()

user = st.session_state.get("username", "test")

# ----------------- 처리 -----------------
results = []

for f in files:
    filename = f.name
    suffix = Path(filename).suffix.lower()

    # 텍스트 디코딩(utf-8 우선, 실패시 cp949 시도)
    raw_bytes = f.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw_bytes.decode("cp949")
        except UnicodeDecodeError:
            st.error(f"파일 인코딩을 알 수 없습니다: {filename}")
            continue

    # --- 마스킹 파이프라인(ML 자리) ---
    masked_text, counts, has_pii = run_masking_pipeline(text)

    # --- 로그 저장(Mongo) ---
    try:
        log_scan(filename=filename, has_pii=has_pii, user=user, counts=counts)
    except Exception as e:
        st.warning(f"로그 저장 실패: {e}")

    # --- 다운로드 버튼 준비 ---
    out_name = f"{Path(filename).stem}_masked{suffix}"
    mime = "text/plain" if suffix == ".txt" else "text/csv"
    data = masked_text.encode("utf-8")
    buf = BytesIO(data)

    # --- 화면 출력 ---
    with st.expander(f"결과 미리보기: {filename}", expanded=True):
        st.write(f"탐지 결과: **{'개인정보 있음' if has_pii else '없음'}**  |  이메일 {counts['email']}건, 주민번호 {counts['rrn']}건")
        st.code(masked_text[:2000] if len(masked_text) > 2000 else masked_text, language="text")
        st.download_button("⬇️ 마스킹 파일 다운로드", data=buf, file_name=out_name, mime=mime)

    results.append({
        "파일명": filename,
        "개인정보 유무": "있음" if has_pii else "없음",
        "이메일 수": counts["email"],
        "주민번호 수": counts["rrn"],
    })

# 간단 요약 테이블
if results:
    st.subheader("스캔 요약")
    st.dataframe(results, use_container_width=True)
