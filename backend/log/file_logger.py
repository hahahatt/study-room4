# backend/log/file_logger.py
from __future__ import annotations
from typing import Optional, Iterable, Any, Dict, List, Tuple
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from .db import get_file_logs_col, get_db
from pymongo.collection import Collection

def _resolve_user_identity(*, db, user_hint: Optional[str] = None) -> Dict[str, Optional[str]]:
    name = None
    email = None
    # 1) Streamlit 세션
    try:
        import streamlit as st
        name = st.session_state.get("user_name") or st.session_state.get("username")
        email = st.session_state.get("user_email") or st.session_state.get("email")
        if name and email:
            return {"user_name": str(name), "user": str(email)}
    except Exception:
        pass
    # 2) DB users 컬렉션
    users_col_name = os.getenv("MONGO_USERS_COLLECTION", "users")
    try:
        users = db[users_col_name]
        q = {}
        if email:
            q = {"email": email}
        elif user_hint and "@" in user_hint:
            q = {"email": user_hint}
        elif user_hint:
            q = {"username": user_hint}
        if q:
            u = users.find_one(q) or {}
            name = u.get("name") or u.get("username") or name
            email = u.get("email") or email
    except Exception:
        pass
    # 3) 로컬파트 폴백
    if not name and email and "@" in email:
        name = email.split("@", 1)[0]
    if not name and user_hint and "@" in user_hint:
        name = user_hint.split("@", 1)[0]
    return {"user_name": name or "사용자", "user": email or (user_hint or "me")}

def log_file_upload(
    *,
    user: Optional[str],
    filename: str,
    size: Optional[int] = None,
    content_type: Optional[str] = None,
    detected_pii: Optional[Dict[str, int]] = None,
    extra: Optional[Dict[str, Any]] = None,
    has_pii: Optional[bool] = None,      # ✅ 새 인자 (에러 해결)
) -> None:
    """
    파일 업로드/스캔 로그 저장 (컬렉션은 get_file_logs_col로 단일화)
    """
    db = get_db()
    ident = _resolve_user_identity(db=db, user_hint=user)
    if has_pii is None:
        # 요약 집계가 있으면 합으로 추정
        total = sum(detected_pii.values()) if isinstance(detected_pii, dict) else 0
        has_pii = total > 0

    doc = {
        "log_type": "file",  # 구분자
        "user": ident["user"],
        "user_name": ident["user_name"],   # 사용자 이름 저장
        "filename": filename,
        "size": size,
        "content_type": content_type,
        "detected_pii": detected_pii or {},
        "has_pii": bool(has_pii),          # ✅ 요청 인자 반영
        "extra": extra or {},
        "uploaded_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
    }
    get_file_logs_col().insert_one(doc)

def list_file_uploads(
    page: int = 1,
    page_size: int = 20,
    *,
    filters: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    col = get_file_logs_col()
    f = filters or {}
    skip = max(0, (page - 1) * page_size)
    cur = col.find(f).sort("uploaded_at", -1).skip(skip).limit(page_size)
    items = list(cur)
    total = col.count_documents(f)
    return items, total

# ✅ 레거시 API 호환 (1_파일 검사.py에서 사용)
def log_scan(*, user: Optional[str], filename: str, detected_pii: Optional[Dict[str, int]] = None,
             size: Optional[int] = None, content_type: Optional[str] = None,
             extra: Optional[Dict[str, Any]] = None, has_pii: Optional[bool] = None) -> None:
    # 새 인자 has_pii 그대로 전달 (에러 방지)
    return log_file_upload(user=user, filename=filename, size=size, content_type=content_type,
                           detected_pii=detected_pii, extra=extra, has_pii=has_pii)

def list_scan_logs(page: int = 1, page_size: int = 20, *, filters: Optional[Dict[str, Any]] = None):
    return list_file_uploads(page=page, page_size=page_size, filters=filters)
