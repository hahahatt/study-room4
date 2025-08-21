# backend/log/email_logger.py
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Iterable, Optional
import os
from .db import get_db
from pymongo.collection import Collection


def _attachment_names(attachments):
    return [getattr(f, "name", "attachment.bin") for f in (attachments or [])]


def _scan_summary_to_dict(df):
    if df is None:
        return None
    try:
        return {str(row["항목"]): int(row["첨부"]) for _, row in df.iterrows()}
    except Exception:
        try: return df.to_dict(orient="records")
        except Exception: return None


def _get_sender_email(credentials) -> Optional[str]:
    try:
        from ..email.gmail_auth import build_gmail_service
        service = build_gmail_service(credentials)
        prof = service.users().getProfile(userId="me").execute()
        return prof.get("emailAddress")
    except Exception:
        return None

def _resolve_username_and_email(*, db, gmail_email: Optional[str]) -> tuple[str, Optional[str]]:
    """
    반환: (username, email)
    우선순위:
      1) st.session_state['username'] (있으면 그대로 username)
      2) users 컬렉션 조회 (username 또는 email로 조회) → username
      3) gmail_email의 로컬파트
      4) '사용자'
    """
    username = None
    email = gmail_email

    # 1) 세션
    try:
        import streamlit as st
        username = st.session_state.get("username") or st.session_state.get("user_name") or username
        email = st.session_state.get("user_email") or st.session_state.get("email") or email
    except Exception:
        pass

    # 2) DB users에서 보강
    users_col = os.getenv("MONGO_USERS_COLLECTION", "users")
    try:
        users = db[users_col]
        user_doc = None
        if username:
            user_doc = users.find_one({"username": username})
        if not user_doc and email:
            user_doc = users.find_one({"email": email})
        if user_doc:
            username = user_doc.get("username") or user_doc.get("name") or username
            email = user_doc.get("email") or email
    except Exception:
        pass

    # 3) 폴백
    if not username and email and "@" in email:
        username = email.split("@", 1)[0]
    if not username:
        username = "사용자"

    return username, email


def log_email_send(
    credentials,
    *,
    to: str,
    subject: str,
    body: str,
    attachments: Optional[Iterable[Any]],
    scan_summary_df=None,
    masked: bool,
) -> None:
    db = get_db()
    col_name = os.getenv("MONGO_EMAILLOGS_COLLECTION", "email_logs")
    col: Collection = db[col_name]

    sender_email = _get_sender_email(credentials)
    username, final_email = _resolve_username_and_email(db=db, gmail_email=sender_email)

    doc = {
        "log_type": "email",
        "user": username,
        "user_name": username,
        # (참고용) 원래 이메일도 남겨두면 추후 문제 분석에 유용
        "user_email": final_email,
        "to": to,
        "subject": subject,
        "body": body,
        "attachment_names": _attachment_names(attachments),
        "scan_summary": _scan_summary_to_dict(scan_summary_df),
        "masked": bool(masked),
        "sent_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
    }
    try:
        col.insert_one(doc)
    except Exception as e:
        try:
            import streamlit as st
            st.warning(f"⚠️ 전송 로그 저장에 실패했습니다: {e}")
        except Exception:
            pass