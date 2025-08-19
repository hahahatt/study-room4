import streamlit as st
import re
from utils import get_policies, extract_urls, classify_urls

st.set_page_config(page_title="이메일 검사", layout="wide", page_icon="📧")
st.markdown("# 📧 이메일 검사")

POL = get_policies(st.session_state)

left, right = st.columns([2,1], vertical_alignment="top")
with left:
    body_text = st.text_area("이메일 본문 붙여넣기", height=240, placeholder="여기에 이메일 내용을 붙여넣으세요.")
with right:
    st.caption("URL/도메인 검사 정책")
    st.write(f"- 블랙 키워드: {', '.join(POL['url_black_keywords'])}")
    st.write(f"- 화이트 도메인: {', '.join(POL['url_white_domains'])}")

uploaded = st.file_uploader("첨부파일(선택, txt만 테스트)", type=["txt"])
if uploaded:
    try:
        body_text += "\n\n" + uploaded.read().decode(errors="ignore")
        st.success(f"첨부 텍스트 병합: {uploaded.name}")
    except Exception:
        st.warning("첨부 텍스트 병합 실패(인코딩 등)")

if not body_text.strip():
    st.stop()

with st.spinner("이메일 분석 중…"):
    # 단순 PII 패턴(데모) – 파일 검사보다 간략
    EMAIL_PAT = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    PHONE_PAT = r"\b01[016789]-?\d{3,4}-?\d{4}\b"

    emails = re.findall(EMAIL_PAT, body_text)
    phones = re.findall(PHONE_PAT, body_text)

    urls = extract_urls(body_text)
    ok_urls, bad_urls = classify_urls(urls, POL)

m1, m2, m3 = st.columns(3)
m1.metric("이메일 주소 수", len(emails))
m2.metric("전화번호 수", len(phones))
m3.metric("URL 수", len(urls))

if bad_urls:
    st.error(f"🚫 의심 URL {len(bad_urls)}건")
    st.write(bad_urls[:10])
else:
    st.success("✅ 의심 URL 없음")

if (len(emails) > 0 or len(phones) > 0) and POL["warn_if_email"]:
    st.warning("⚠️ 메일 본문에 개인정보 가능성이 있습니다. 전송 전 재검토하세요.")
else:
    st.info("개인정보 의심 패턴이 낮습니다.")

with st.expander("본문 미리보기"):
    st.text_area("이메일 본문", body_text[:6000], height=260)
