# backend/db.py
import os
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("MONGO_DB", "insiderlock")
SCAN_LOGS_COL = os.getenv("MONGO_SCANLOGS_COLLECTION", "scan_logs")

_client = None
_db = None
_scan_logs = None

def get_db():
    global _client, _db, _scan_logs
    if _db is None:
        if not MONGO_URL:
            raise RuntimeError("MONGO_URL이 .env에 없습니다.")
        _client = MongoClient(MONGO_URL)
        _db = _client[DB_NAME]
        _scan_logs = _db[SCAN_LOGS_COL]
        # 조회 효율 & 중복 방지용(원하면)
        try:
            _scan_logs.create_index([("detected_at_utc", ASCENDING)])
            _scan_logs.create_index([("detected_at_kst", ASCENDING)])
            _scan_logs.create_index([("filename", ASCENDING)])
            _scan_logs.create_index([("user", ASCENDING)])
        except Exception:
            pass
    return _db

def get_scan_logs_col():
    get_db()
    return _scan_logs