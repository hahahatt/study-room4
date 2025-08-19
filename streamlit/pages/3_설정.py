import os, json, re
import streamlit as st

# utils 불러오기 (st_app/에 있으니까 바로 import)
from utils import (
    get_patterns,
    get_policies,
    DEFAULT_PATTERNS,
    DEFAULT_POLICIES
)


st.set_page_config(page_title="설정", layout="wide", page_icon="⚙️")
st.markdown("# ⚙️ 설정")

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "settings.json")

# ─────────────────────────────────────────────────────────────
# 1) 현재 세션의 패턴/정책 로드
# ─────────────────────────────────────────────────────────────
PATTERNS = get_patterns(st.session_state)
POLICIES = get_policies(st.session_state)

# ─────────────────────────────────────────────────────────────
# 2) 디스크에 저장된 설정을 세션에 반영 (최초 1회)
# ─────────────────────────────────────────────────────────────
if "loaded_from_file" not in st.session_state:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 패턴
            if "patterns" in saved and isinstance(saved["patterns"], dict):
                PATTERNS.update(saved["patterns"])
            # 정책
            if "policies" in saved and isinstance(saved["policies"], dict):
                POLICIES.update(saved["policies"])
            st.toast("디스크 설정을 불러왔습니다.", icon="✅")
        except Exception as e:
            st.warning(f"설정 파일을 불러오지 못했습니다: {e}")
    st.session_state.loaded_from_file = True

# ─────────────────────────────────────────────────────────────
# 3) UI: 패턴/정책 편집
# ─────────────────────────────────────────────────────────────
colA, colB = st.columns([1,1], vertical_alignment="top")

with colA:
    st.subheader("🧾 탐지 패턴 (Regex)")
    st.caption("잘못된 정규표현식은 저장 시 자동 검증됩니다.")
    pat_inputs = {}
    for k in ["주민등록번호", "이메일", "전화번호"]:
        pat_inputs[k] = st.text_input(k, PATTERNS.get(k, DEFAULT_PATTERNS[k]), key=f"pat_{k}")

    with st.expander("커스텀 패턴 추가", expanded=False):
        new_key = st.text_input("패턴 이름 (예: 계좌번호)", key="new_pat_key")
        new_val = st.text_input("정규표현식", key="new_pat_val")
        if st.button("➕ 패턴 추가"):
            if not new_key.strip():
                st.error("패턴 이름을 입력하세요.")
            elif new_key in pat_inputs or new_key in PATTERNS:
                st.error("이미 존재하는 패턴 이름입니다.")
            else:
                try:
                    re.compile(new_val)
                    PATTERNS[new_key] = new_val
                    st.success(f"추가 완료: {new_key}")
                    st.rerun()
                except re.error as e:
                    st.error(f"정규표현식 오류: {e}")

with colB:
    st.subheader("🔑 정책")
    POLICIES["block_if_rrn"] = st.checkbox("주민등록번호 포함 시 차단", POLICIES["block_if_rrn"])
    POLICIES["warn_if_email"] = st.checkbox("이메일 포함 시 경고", POLICIES["warn_if_email"])

    st.divider()
    st.subheader("📦 업로드 제한")
    POLICIES["max_files"] = st.number_input("파일 최대 개수", min_value=1, max_value=100, value=int(POLICIES["max_files"]))
    POLICIES["max_total_mb"] = st.number_input("총 용량 제한(MB)", min_value=1.0, max_value=500.0, value=float(POLICIES["max_total_mb"]))

    st.divider()
    st.subheader("🌐 URL 정책 (이메일 검사)")
    black = ", ".join(POLICIES.get("url_black_keywords", []))
    white = ", ".join(POLICIES.get("url_white_domains", []))
    black = st.text_area("블랙 키워드 (쉼표로 구분)", black, height=70)
    white = st.text_area("화이트 도메인 (쉼표로 구분)", white, height=70)
    POLICIES["url_black_keywords"] = [s.strip() for s in black.split(",") if s.strip()]
    POLICIES["url_white_domains"]  = [s.strip() for s in white.split(",") if s.strip()]

# 패턴 미리보기 간단 검사
with st.expander("🧪 정규표현식 테스트", expanded=False):
    test_text = st.text_area("테스트 텍스트", value="예: 주민등록번호 800101-1234567 / 이메일 test@example.com / 전화 010-1234-5678")
    if st.button("테스트 실행"):
        try:
            sample_counts = {k: len(re.findall(v, test_text)) for k, v in {**PATTERNS, **pat_inputs}.items()}
            st.success("매칭 결과:")
            st.json(sample_counts)
        except re.error as e:
            st.error(f"정규표현식 오류: {e}")

# ─────────────────────────────────────────────────────────────
# 4) 저장 / 초기화
# ─────────────────────────────────────────────────────────────
btn1, btn2, btn3 = st.columns(3)

def _validate_and_merge():
    # 입력된 패턴 유효성 검사 후 세션에 반영
    for name, pat in pat_inputs.items():
        try:
            re.compile(pat)
            PATTERNS[name] = pat
        except re.error as e:
            st.error(f"[{name}] 정규표현식 오류: {e}")
            return False
    return True

with btn1:
    if st.button("💾 설정 저장", use_container_width=True):
        if _validate_and_merge():
            os.makedirs(CONFIG_DIR, exist_ok=True)
            payload = {"patterns": PATTERNS, "policies": POLICIES}
            try:
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                st.success("설정이 저장되었습니다. 모든 페이지에 즉시 반영됩니다 ✅")
            except Exception as e:
                st.error(f"저장 실패: {e}")

with btn2:
    if st.button("🔁 기본값으로 복원", use_container_width=True):
        st.session_state.patterns = DEFAULT_PATTERNS.copy()
        st.session_state.policies = DEFAULT_POLICIES.copy()
        try:
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
        except Exception:
            pass
        st.success("기본값으로 초기화했습니다.")
        st.rerun()

with btn3:
    if st.button("↻ 새로고침", use_container_width=True):
        st.rerun()

