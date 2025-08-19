import streamlit as st
import re

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
    st.title("이메일 검사")
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

to = st.text_input("수신자", "example@company.com")
subj = st.text_input("제목")
body = st.text_area("본문", height=180)
atts = st.file_uploader("첨부(옵션)", accept_multiple_files=True)

if st.button("분석하기"):
    risk = 0
    findings = []

    for addr in [a.strip() for a in to.split(",") if a.strip()]:
        if not addr.endswith("@company.com"):
            risk += 2
            findings.append(f"외부 도메인 수신자: {addr}")

    BAD_WORDS = ["주민번호", "계좌번호", "패스워드", "비밀번호", "card number"]
    hit = [w for w in BAD_WORDS if w in body]
    if hit:
        risk += len(hit)
        findings.append(f"민감 표현 포함: {', '.join(hit)}")

    urls = re.findall(r"https?://\S+", body)
    if urls:
        risk += len(urls)
        findings.append(f"본문 URL {len(urls)}건: " + ", ".join(urls[:3]))

    level = "안전" if risk == 0 else ("주의" if risk < 3 else "차단 권고")
    st.subheader(f"결론: {level} (점수 {risk})")
    for fnd in findings:
        st.write("•", fnd)

    if level != "안전":
        st.warning("민감 표현 제거, 외부 수신자 확인, 링크 재검토 후 다시 분석하세요.")
