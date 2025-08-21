# backend/log/query.py
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import re, os
from .db import get_db, get_file_logs_col

PII_KEYS = ["이름","주민번호","전화번호","이메일","카드번호","주소","계좌번호"]

def _email_col():
    db = get_db()
    return db[os.getenv("MONGO_EMAILLOGS_COLLECTION", "email_logs")]

def _file_cols():
    """
    파일 로그는 scan_logs/file_logs가 혼재할 수 있어서
    - 환경변수 우선(MONGO_FILELOGS_COLLECTION, MONGO_SCANLOGS_COLLECTION)
    - 둘 다 없으면 존재하는 이름 감지 → 둘 다 있으면 둘 다 반환
    """
    db = get_db()
    names = set()
    env1 = os.getenv("MONGO_FILELOGS_COLLECTION")
    env2 = os.getenv("MONGO_SCANLOGS_COLLECTION")
    if env1: names.add(env1)
    if env2: names.add(env2)
    if not names:
        try:
            existing = set(db.list_collection_names())
        except Exception:
            existing = set()
        if "scan_logs" in existing: names.add("scan_logs")
        if "file_logs" in existing: names.add("file_logs")
    if not names:
        names.add("scan_logs")
    return [db[n] for n in sorted(names)]

def ensure_indexes():
    try:
        _email_col().create_index([("sent_at", -1)])
        _email_col().create_index([("user", 1), ("user_name", 1)])
        _email_col().create_index([("to", 1)])
        _email_col().create_index([("subject", "text"), ("body", "text")])
    except Exception: pass
    for col in _file_cols():
        try:
            col.create_index([("uploaded_at", -1)])
            col.create_index([("user", 1), ("user_name", 1)])
            col.create_index([("filename", 1)])
        except Exception:
            pass

def _regex(q: str):
    return {"$regex": re.escape(q), "$options": "i"}

def build_filter(keyword=None, masked=None, user=None, to=None, date_from=None, date_to=None) -> Dict[str, Any]:
    f: Dict[str, Any] = {}
    if masked is not None: f["masked"] = masked
    if user: f["$or"] = [{"user": _regex(user)}, {"user_name": _regex(user)}]
    if to: f["to"] = _regex(to)
    if date_from or date_to:
        cond = {}
        if date_from: cond["$gte"] = f"{date_from}T00:00:00+09:00"
        if date_to:   cond["$lte"] = f"{date_to}T23:59:59.999999+09:00"
        f["sent_at"] = cond
    if keyword:
        f.setdefault("$or", []).extend([{"subject": _regex(keyword)}, {"body": _regex(keyword)}])
    return f

def build_file_filter(keyword=None, user=None, date_from=None, date_to=None) -> Dict[str, Any]:
    f: Dict[str, Any] = {}
    if user: f["$or"] = [{"user": _regex(user)}, {"user_name": _regex(user)}]
    if keyword: f["filename"] = _regex(keyword)
    if date_from or date_to:
        cond = {}
        if date_from: cond["$gte"] = f"{date_from}T00:00:00+09:00"
        if date_to:   cond["$lte"] = f"{date_to}T23:59:59.999999+09:00"
        f["uploaded_at"] = cond
    return f

def _display_name(doc: Dict[str, Any]) -> str:
    if doc.get("user_name"): return str(doc["user_name"])
    u = doc.get("user") or ""
    return u.split("@", 1)[0] if "@" in u else (u or "사용자")

def list_email_logs(page: int = 1, page_size: int = 20, *, filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], int]:
    ensure_indexes()
    col = _email_col()
    f = filters or {}
    skip = max(0, (page - 1) * page_size)
    cur = col.find(f).sort("sent_at", -1).skip(skip).limit(page_size)
    items: List[Dict[str, Any]] = []
    for doc in cur:
        d = {
            "log_type": doc.get("log_type", "email"),
            "user_display": _display_name(doc),
            "to": doc.get("to"),
            "subject": doc.get("subject"),
            "attachment_names": doc.get("attachment_names", []),
            "masked": "O" if doc.get("masked", False) else "X",  # O/X
            "sent_at": doc.get("sent_at"),
            "scan_summary": doc.get("scan_summary") or {},
        }
        if isinstance(d["scan_summary"], dict):
            for k in PII_KEYS:
                d[f"scan_{k}"] = int(d["scan_summary"].get(k, 0))
        else:
            for k in PII_KEYS:
                d[f"scan_{k}"] = 0
        items.append(d)
    total = col.count_documents(f)
    return items, total

def list_file_logs(page: int = 1, page_size: int = 20, *, filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], int]:
    """
    scan_logs / file_logs 양쪽에 있는 데이터를 '합쳐서' 페이지네이션.
    (대량 데이터가 아니라면 충분히 빠름)
    """
    ensure_indexes()
    f = filters or {}
    # 모든 후보 컬렉션에서 가져와 합치기
    merged: List[Dict[str, Any]] = []
    for col in _file_cols():
        for doc in col.find(f):
            detected = doc.get("detected_pii") or {}
            merged.append({
                "log_type": doc.get("log_type", "file"),
                "uploaded_at": doc.get("uploaded_at"),
                "user_display": _display_name(doc),
                "filename": doc.get("filename"),
                "size": doc.get("size"),
                "content_type": doc.get("content_type"),
                **{f"scan_{k}": int(detected.get(k, 0)) if isinstance(detected, dict) else 0 for k in PII_KEYS},
            })
    # 업로드 시각 기준 내림차순 정렬
    merged.sort(key=lambda x: x.get("uploaded_at") or "", reverse=True)
    total = len(merged)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    return merged[start:end], total

__all__ = ["PII_KEYS", "build_filter", "list_email_logs", "ensure_indexes", "build_file_filter", "list_file_logs"]
