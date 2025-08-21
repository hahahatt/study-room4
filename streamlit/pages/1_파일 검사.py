import streamlit as st
from io import BytesIO
from pathlib import Path
import sys
import mimetypes

# ----------------- import 경로 세팅 -----------------
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# ✅ 이메일 페이지와 동일한 로직 직접 사용
from backend.email.email_scanner import scan_email, summarize_email
from backend.email.mask_attachments import mask_attachment
from backend.log.file_logger import log_scan


# 홈페이지 로고
from backend.ui import show_logo
show_logo(max_width=400, pad=2, compact=True)  # 크키, 여백 조절 가능



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

# ----------------- 본문 : 파일 업로드 ---------------------------
# ⬇️ 이메일 페이지와 동일하게, 다양한 첨부 타입 허용
files = st.file_uploader(
    "파일 업로드",
    accept_multiple_files=True,
    type=["txt", "csv", "docx", "pdf", "xlsx", "jpg", "jpeg", "png"]
)
if not files:
    st.caption("샘플: .txt, .docx, .pdf, .xlsx, 이미지 파일을 올려보세요.")
    st.stop()

user = st.session_state.get("username", "test")

# ----------------- 처리 -----------------
rows = []

for f in files:
    filename = f.name
    suffix = Path(filename).suffix.lower()

    # 1) 스캔: 이메일 페이지와 같게 scan_email → warnings만 사용(본문은 공백)
    try:
        try: f.seek(0)
        except Exception: pass
        warnings, _masked_body = scan_email(subject="", body="", attachments=[f])
    except Exception as e:
        st.error(f"스캔 실패: {filename} — {e}")
        continue

    # 2) 요약표: summarize_email(첨부만) → dict로 변환
    counts = {}
    try:
        try: f.seek(0)
        except Exception: pass
        df = summarize_email(subject="", body="", attachments=[f])
        if df is not None:
            counts = {str(row["항목"]): int(row["첨부"]) for _, row in df.iterrows()}
    except Exception:
        counts = {}

    total = sum(counts.values()) if isinstance(counts, dict) else 0
    has_pii = bool(warnings) or (total > 0)

    # 3) 마스킹: 이메일 페이지와 동일—민감정보 있을 때만 첨부 마스킹 실행
    masked_bytes = None
    masked_name = None
    if has_pii:
        try:
            try: f.seek(0)
            except Exception: pass
            mf = mask_attachment(f)  # BytesIO 반환(성공 시), 실패 시 None
            if mf is not None:
                masked_name = getattr(mf, "name", f"masked_{filename}") or f"masked_{filename}"
                masked_bytes = mf.getvalue()
        except Exception as e:
            st.warning(f"마스킹 실패: {filename} — {e}")

    # 4) 로그 저장 (파일 로그)
    try:
        size = getattr(f, "size", None)
        content_type = getattr(f, "type", None) or (mimetypes.guess_type(filename)[0] or "application/octet-stream")
        log_scan(
            filename=filename,
            user=user,                 # logger가 DB에서 user_name 확정
            detected_pii=counts,
            has_pii=has_pii,
            size=size,
            content_type=content_type,
        )
    except Exception as e:
        st.warning(f"로그 저장 실패: {e}")

    # 5) 화면 출력
    with st.expander(f"결과: {filename}", expanded=True):
        # 이메일 페이지처럼 '요약표(첨부만)'을 보여줌
        st.markdown("**스캔 요약본 (첨부만)**")
        if df is not None and not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("요약 정보가 없습니다.")

        # 상태 표시
        st.write(f"탐지 결과: **{'개인정보 있음' if has_pii else '없음'}**")

        # 다운로드(마스킹 성공 시에만 제공; 이메일 페이지와 동일한 정책)
        if has_pii and masked_bytes is not None and masked_name:
            mime = mimetypes.guess_type(masked_name)[0] or "application/octet-stream"
            st.download_button("⬇️ 마스킹 파일 다운로드", data=masked_bytes, file_name=masked_name, mime=mime)
        elif not has_pii:
            st.caption("민감 정보가 없어 마스킹 없이 원본 유지")

    # 요약 테이블용 간단 행
    rows.append({
        "파일명": filename,
        "개인정보 유무": "있음" if has_pii else "없음",
        "총 검출 수": total,
        "이메일": counts.get("이메일", 0),
        "주민번호": counts.get("주민번호", 0),
        "전화번호": counts.get("전화번호", 0),
        "카드번호": counts.get("카드번호", 0),
        "주소": counts.get("주소", 0),
        "계좌번호": counts.get("계좌번호", 0),
    })

# 간단 요약 테이블(여러 파일 업로드 시 모아보기)
if rows:
    st.subheader("스캔 요약")
    st.dataframe(rows, use_container_width=True, hide_index=True)
