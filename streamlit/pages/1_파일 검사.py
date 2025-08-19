import streamlit as st
import re

st.title("파일 검사")

files = st.file_uploader("파일 업로드", accept_multiple_files=True, type=["txt"])
if not files:
    st.caption("샘플: .txt 파일을 올려보세요 (주민번호, 이메일 탐지 예시).")
    st.stop()

PATTERNS = {
    "주민등록번호": r"\b\d{6}-\d{7}\b",
    "이메일": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "전화번호": r"\b01[016789]-?\d{3,4}-?\d{4}\b",
}

for f in files:
    st.subheader(f"파일: {f.name}")
    text = f.read().decode(errors="ignore")

    results = {}
    for name, pat in PATTERNS.items():
        results[name] = re.findall(pat, text)

    cols = st.columns(len(PATTERNS))
    for i, (k, v) in enumerate(results.items()):
        cols[i].metric(k, len(v))

    if st.toggle("마스킹 보기", key=f"mask_{f.name}"):
        masked = text
        for name, pat in PATTERNS.items():
            if name == "이메일":
                masked = re.sub(pat, lambda m: m.group(0).split("@")[0][:2] + "***@***", masked)
            elif name == "주민등록번호":
                masked = re.sub(pat, "******-*******", masked)
            elif name == "전화번호":
                masked = re.sub(pat, "***-****-****", masked)
        st.text_area("미리보기(마스킹 적용)", masked, height=200)
    else:
        st.text_area("미리보기(원본)", text[:2000], height=200)

    st.divider()
