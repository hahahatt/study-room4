# backend/file_logger.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .db import get_scan_logs_col

# 서울 시간대 설정
KST = ZoneInfo("Asia/Seoul")

def log_scan(filename: str, has_pii: bool, user: str, counts=None):
    col = get_scan_logs_col()

    # 한국 시간은 Date time으로 
    # 1) MongoDB용: UTC Date (naive, UTC 기준)
    now_utc = datetime.utcnow()  # naive UTC -> Mongo가 Date로 저장

    # 2) 보기용: KST 문자열(ISO8601)
    now_kst = now_utc.replace(tzinfo=timezone.utc).astimezone(KST)
    kst_str = now_kst.isoformat(timespec="seconds")  # 예: 2025-08-19T12:34:56+09:00

    doc = {
        "filename": filename,
        "has_pii": bool(has_pii),
        "detected_at_utc": now_utc,      # Date 타입(정렬/쿼리용)
        "detected_at_kst": kst_str,      # 사람이 보기 쉬운 KST
        "user": user or "unknown",
    }
    if counts:
        doc["counts"] = counts

    col.insert_one(doc)