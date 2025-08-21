# backend/log/db.py
from __future__ import annotations
import os
from typing import Optional
from pymongo import MongoClient
from dotenv import load_dotenv

_client: Optional[MongoClient] = None
_db = None

def get_db():
    global _client, _db
    if _db is not None:
        return _db
    load_dotenv()
    mongo_url = os.getenv("MONGO_URL")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is not set in .env")
    mongo_db = os.getenv("MONGO_DB", "insiderlock")
    _client = MongoClient(
        mongo_url,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
    )
    _client.admin.command("ping")
    _db = _client[mongo_db]
    return _db

def get_file_logs_col():
    """
    파일 로그 컬렉션을 하나로 통일해서 반환. 실수로 scan_logs랑 file_logs가 생김...
    우선순위:
      1) 환경변수 MONGO_FILELOGS_COLLECTION
      2) 환경변수 MONGO_SCANLOGS_COLLECTION (레거시)
      3) 존재하는 컬렉션 감지: scan_logs > file_logs
      4) 기본값: scan_logs  (레거시 호환)
    """
    db = get_db()
    env_name = os.getenv("MONGO_FILELOGS_COLLECTION") or os.getenv("MONGO_SCANLOGS_COLLECTION")
    if env_name:
        return db[env_name]
    try:
        names = set(db.list_collection_names())
    except Exception:
        names = set()
    if "scan_logs" in names:
        return db["scan_logs"]
    if "file_logs" in names:
        return db["file_logs"]
    return db["scan_logs"]  # 기본을 scan_logs로

# 
def get_scan_logs_col():
    return get_file_logs_col()
