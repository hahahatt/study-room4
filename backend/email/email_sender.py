import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
import base64
import mimetypes
from io import BytesIO

from .gmail_auth import build_gmail_service
from .email_scanner import scan_email
from .mask_attachments import mask_attachment  # 마스킹 모듈

mimetypes.add_type("text/csv", ".csv")
mimetypes.add_type("application/pdf", ".pdf")
mimetypes.add_type("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx")
mimetypes.add_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx")

def _read_all_bytes(file_obj) -> bytes:
    try:
        file_obj.seek(0)
    except Exception:
        pass
    return file_obj.read()


# ─────────────────────────────────────
# 📎 첨부파일 붙이기 (MIME 타입 정확 지정 + filename 파라미터)
# ─────────────────────────────────────
def attach_file(message: MIMEMultipart, file_obj):
    """
    message: 이메일 MIMEMultipart
    file_obj: UploadedFile 또는 BytesIO (name 속성이 있어야 함)
    """
    filename = getattr(file_obj, "name", None) or "attachment.bin"

    # MIME 타입 추론 (확장자 기반)
    ctype, encoding = mimetypes.guess_type(filename)
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"
    maintype, subtype = ctype.split("/", 1)

    data = _read_all_bytes(file_obj)

    # 텍스트류는 MIMEText, 그 외는 MIMEApplication 사용 권장
    # (일부 클라이언트가 text/* 를 txt로 취급하는 경우가 있으니 filename을 반드시 지정!)
    if maintype == "text":
        # 인코딩/한글 깨짐 방지를 위해 utf-8 명시
        try:
            text_str = data.decode("utf-8", errors="replace")
        except Exception:
            # 혹시 디코딩 실패하면 application/octet-stream로 보냄
            part = MIMEApplication(data, _subtype=subtype)
            part.add_header("Content-Disposition", "attachment", filename=filename)
            message.attach(part)
            return

        part = MIMEText(text_str, _subtype=subtype, _charset="utf-8")
        # Content-Transfer-Encoding은 MIMEText가 자동 설정
        # filename은 RFC2231 규격으로 안전하게 추가
        part.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(part)
    else:
        # 이진류는 MIMEApplication로 안전하게
        part = MIMEApplication(data, _subtype=subtype)
        # base64 인코딩은 MIMEApplication가 자동으로 적절 처리하지만,
        # 일부 환경에서 명시적으로 해도 무방
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(part)


# ─────────────────────────────────────
# ✉️ Gmail 전송
# ─────────────────────────────────────
def send_email(credentials, to, subject, body, attachments=None):
    try:
        service = build_gmail_service(credentials)

        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        message.attach(MIMEText(body, "plain", _charset="utf-8"))

        # 첨부파일 추가 (MIME 타입 정확 지정)
        if attachments:
            for file_obj in attachments:
                try:
                    file_obj.seek(0)
                except Exception:
                    pass
                attach_file(message, file_obj)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

    except Exception as e:
        import traceback
        st.error(f"❌ 메일 전송 실패:\n{traceback.format_exc()}")


# ─────────────────────────────────────
# 🖥️ Streamlit UI
# ─────────────────────────────────────
def send_email_ui(credentials):
    st.header("📧 내부 임직원 메일 발송 시스템")

    to = st.text_input("받는 사람 이메일", placeholder="example@example.com")
    subject = st.text_input("제목", placeholder="제목을 입력하세요")
    body = st.text_area("본문 입력", placeholder="내용을 입력하세요", height=150)
    attachments = st.file_uploader(
        "📎 첨부파일 업로드",
        type=["txt", "csv", "xlsx", "pdf", "docx", "hwp", "jpg","png"],
        accept_multiple_files=True
    )

    # 세션 상태
    if "confirm_send" not in st.session_state:
        st.session_state.confirm_send = False
    if "masked_body" not in st.session_state:
        st.session_state.masked_body = ""
    if "last_inputs" not in st.session_state:
        st.session_state.last_inputs = {}

    # 1) 탐지 후 전송 버튼
    if st.button("🔍 민감 정보 및 개인정보 탐지 후 전송합니다."):
        # 유효성 검사
        if not to or "@" not in to:
            st.error("❌ 받는 사람 이메일 주소를 올바르게 입력하세요.")
            return
        if not subject:
            st.error("❌ 제목을 입력하세요.")
            return
        if not body:
            st.error("❌ 본문을 입력하세요.")
            return

        # 본문/제목/첨부 민감정보 탐지 + 본문 마스킹
        warnings, masked_body = scan_email(subject, body, attachments)

        if warnings:
            st.warning("⚠️ 민감 정보가 감지되었습니다. 마스킹 후 전송을 원하시면 아래 버튼을 클릭하세요.")
            for w in warnings:
                st.write(f"• {w}")

            # 첨부파일을 '마스킹된 버전'으로 변환해 세션에 보관
            masked_files = []
            if attachments:
                for f in attachments:
                    try:
                        f.seek(0)
                    except Exception:
                        pass

                    mf = mask_attachment(f)  # BytesIO 반환, 이름: masked_원본명
                    if mf is None:
                        # 실패 시 원본도 유지되도록 복사
                        f.seek(0)
                        copied = BytesIO(f.read())
                        copied.name = getattr(f, "name", "attachment.bin")
                        masked_files.append(copied)
                    else:
                        # 이름이 확장자를 포함하고 있는지 한 번 더 보장
                        if not hasattr(mf, "name") or not mf.name:
                            mf.name = "masked_" + (getattr(f, "name", "attachment.bin"))
                        masked_files.append(mf)

            st.session_state.masked_body = masked_body
            st.session_state.confirm_send = True
            st.session_state.last_inputs = {
                "to": to,
                "subject": subject,
                "attachments": masked_files
            }
        else:
            # 경고 없음: 원문 본문 + 원본 첨부 그대로 전송
            if attachments:
                for f in attachments:
                    # ★ 추가: 전송 전에 포인터 초기화
                    try:
                        f.seek(0)
                    except Exception:
                        pass
            send_email(credentials, to, subject, body, attachments)
            st.success("✅ 민감 정보 없음: 이메일 전송 완료!")

    # 2) 마스킹 후 전송 계속
    if st.session_state.confirm_send:
        if st.button("📛 마스킹 후 전송 계속"):
            inputs = st.session_state.last_inputs
            send_email(
                credentials,
                inputs["to"],
                inputs["subject"],
                st.session_state.masked_body,
                inputs["attachments"],
            )
            st.success("✅ 마스킹 후 이메일 전송 완료!")

            # 상태 초기화
            st.session_state.confirm_send = False
            st.session_state.masked_body = ""
            st.session_state.last_inputs = {}
