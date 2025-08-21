# backend/masking.py
from __future__ import annotations
from typing import Optional, Dict, Any, Iterable, Tuple, List
from io import BytesIO

# ✅ 최신 로직: email 폴더의 구현을 그대로 사용
from .email.pii_masker import mask_text as _mask_text_core  # 텍스트 마스킹
from .email.mask_attachments import mask_attachment as _mask_attachment_core  # 첨부 마스킹
from .email.email_scanner import summarize_email as _summarize_email  # NER+정규식 집계(첨부만)

# ─────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────
def _seek0(f):
    try: f.seek(0)
    except: pass

def _clone_bytesio(src) -> BytesIO:
    """업로드 파일을 BytesIO로 복사(name 보존)."""
    _seek0(src)
    data = src.read()
    bio = BytesIO(data)
    bio.name = getattr(src, "name", "attachment.bin")
    return bio

def _df_to_summary_dict(df) -> Dict[str, int]:
    """summarize_email(DataFrame) → {'항목': count}"""
    if df is None:
        return {}
    try:
        return {str(row["항목"]): int(row["첨부"]) for _, row in df.iterrows()}
    except Exception:
        try:
            # 혹시 포맷이 다르면 records를 합산
            tmp = {}
            for r in df.to_dict(orient="records"):
                k = str(r.get("항목"))
                v = int(r.get("첨부") or 0)
                tmp[k] = tmp.get(k, 0) + v
            return tmp
        except Exception:
            return {}

# ─────────────────────────────────────────
# 공개 API (이전 코드 호환 이름)
# ─────────────────────────────────────────
def mask_text(text: str) -> str:
    """최신 NER+정규식 기반 텍스트 마스킹"""
    return _mask_text_core(text or "")

def detect_pii_in_file(file_obj) -> Dict[str, int]:
    """단일 첨부에서 PII 항목별 개수 집계 (첨부만)"""
    # summarize_email(subject, body, attachments) → DF
    try:
        df = _summarize_email(subject="", body="", attachments=[file_obj])
        return _df_to_summary_dict(df)
    finally:
        _seek0(file_obj)

def mask_file(file_obj):
    """단일 첨부 마스킹. 성공 시 BytesIO(name 포함), 실패 시 None."""
    try:
        _seek0(file_obj)
        masked = _mask_attachment_core(file_obj)
        if masked is not None and (not hasattr(masked, "name") or not masked.name):
            masked.name = "masked_" + (getattr(file_obj, "name", "attachment.bin"))
        return masked
    finally:
        _seek0(file_obj)

# 편의: 리스트 처리
def mask_files(files: Iterable) -> List:
    out = []
    for f in (files or []):
        mf = mask_file(f)
        if mf is None:
            out.append(_clone_bytesio(f))  # 실패 시 원본 복제
        else:
            out.append(mf)
    return out

def scan_file(file_obj) -> Tuple[bool, Dict[str, int]]:
    """
    파일 하나 스캔 → (has_pii, detected_pii)
    has_pii는 요약 합계 > 0 여부.
    """
    summary = detect_pii_in_file(file_obj)
    total = sum(summary.values()) if isinstance(summary, dict) else 0
    return (total > 0), summary

# (옵션) 예전 함수명이 있다면 아래처럼 alias 해도 좋습니다.
# detect_pii = detect_pii_in_file
