from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import re

# ---- 선택적(NER) 의존성: 없으면 정규식만 동작 ----
USE_NER = True
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForTokenClassification
except Exception:
    USE_NER = False

# =========================
# 패턴 (정규식 기반 탐지/마스킹)
# =========================
RE_EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
RE_RRN   = re.compile(r"\b\d{6}-\d{7}\b")
RE_PHONE = re.compile(r"\b\d{2,3}-\d{3,4}-\d{4}\b")
RE_CARD  = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{4}\b")

def _regex_counts(text: str) -> Dict[str, int]:
    return {
        "email": len(RE_EMAIL.findall(text)),
        "rrn":   len(RE_RRN.findall(text)),
        "phone": len(RE_PHONE.findall(text)),
        "card":  len(RE_CARD.findall(text)),
        "name":  0,
    }

def _regex_mask(text: str) -> str:
    txt = RE_RRN.sub(lambda m: m.group(0)[:6] + "-*******", text)
    txt = RE_PHONE.sub(lambda m: m.group(0)[:3] + "-****-" + m.group(0)[-4:], txt)
    txt = RE_EMAIL.sub(lambda m: m.group(1)[0] + "***@" + m.group(2), txt)
    txt = RE_CARD.sub(lambda m: f"{m.group(0)[:4]}-****-****-{m.group(0)[-4:]}", txt)
    return txt

# =========================
# NER 모델 (있으면 사용, 없으면 정규식만)
# =========================
LABEL_LIST = [
    "O", "B-이름", "I-이름",
    "B-주민번호", "I-주민번호",
    "B-전화번호", "I-전화번호",
    "B-이메일", "I-이메일",
    "B-카드번호", "I-카드번호",
]
ID2LABEL = {i: lab for i, lab in enumerate(LABEL_LIST)}

_tokenizer = None   # <- 잘못된 초기화 제거!
_model = None
_device = "cpu"

def _find_model_dir() -> Path | None:
    """모델 폴더 탐색: <repo>/model/ner_model → <repo>/backend/ner_model → 현재폴더/ner_model"""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "model" / "ner_model",
        here.parent / "ner_model",
        here.parent.parent / "model" / "ner_model",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def _ensure_model():
    """필요 시 NER 모델/토크나이저 로드. 실패하면 정규식 모드로 폴백."""
    global _tokenizer, _model, _device, USE_NER
    if not USE_NER:
        return
    if _tokenizer is not None and _model is not None:
        return

    model_dir = _find_model_dir()
    if not model_dir:
        # 모델 폴더가 없으면 정규식 모드만 사용
        USE_NER = False
        return

    try:
        _tokenizer = AutoTokenizer.from_pretrained(
            str(model_dir), use_fast=True, local_files_only=True
        )
        _model = AutoModelForTokenClassification.from_pretrained(
            str(model_dir), local_files_only=True
        )
        _model.eval()
        _device = "cuda" if (hasattr(torch, "cuda") and torch.cuda.is_available()) else "cpu"
        _model.to(_device)
    except Exception as e:
        # 어떤 이유로든 로드 실패 → 정규식 모드
        USE_NER = False
        _tokenizer = None
        _model = None
        print(f"[masking] NER 모델 로드 실패(정규식 모드로 동작): {e}")

def _ner_predict(text: str) -> List[Tuple[str, str]]:
    """문자 단위 BIO 라벨링 결과를 (문자, 태그) 리스트로 반환."""
    _ensure_model()
    if not USE_NER or _tokenizer is None or _model is None:
        return []

    tokens = list(text)

    # 1) 토크나이즈 (BatchEncoding 유지)
    enc = _tokenizer(
        tokens,
        is_split_into_words=True,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )

    # 2) word_ids 가져오기 (fast 토크나이저 전용)
    word_ids = enc.word_ids(0) if hasattr(enc, "word_ids") else None

    # 3) 텐서만 디바이스로 이동 (메서드 유지)
    if hasattr(enc, "to"):
        enc = enc.to(_device)

    # 4) 추론
    with torch.no_grad():
        output = _model(**enc)
    predictions = output.logits.argmax(dim=-1).squeeze().tolist()

    # 5) 매핑 없으면(슬로우 토크나이저) 폴백: 1:1 가정
    if word_ids is None:
        merged = []
        limit = min(len(tokens), len(predictions))
        for i in range(limit):
            merged.append((tokens[i], ID2LABEL[predictions[i]]))
        return merged

    # 6) fast 경로: word_ids로 문자 인덱스 매핑
    merged = []
    prev_wid = None
    for idx, wid in enumerate(word_ids):
        if wid is None or wid == prev_wid:
            continue
        merged.append((tokens[wid], ID2LABEL[predictions[idx]]))
        prev_wid = wid
    return merged

def _merge_entities(tagged_tokens: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """BIO를 이어서 (원문조각, 엔티티라벨) 리스트로 합침."""
    res: List[Tuple[str, str]] = []
    cur_tag = None
    cur_text = ""
    for ch, tag in tagged_tokens:
        if tag.startswith("B-"):
            if cur_tag:
                res.append((cur_text, cur_tag))
            cur_tag = tag[2:]
            cur_text = ch
        elif tag.startswith("I-") and cur_tag == tag[2:]:
            cur_text += ch
        else:
            if cur_tag:
                res.append((cur_text, cur_tag))
                cur_tag = None
            cur_text = ""
    if cur_tag:
        res.append((cur_text, cur_tag))
    return res

def _mask_entity(piece: str, label: str) -> str:
    if label == "이름":
        return (piece[0] + "**") if piece else piece
    if label == "주민번호":
        return RE_RRN.sub(lambda m: m.group(0)[:6] + "-*******", piece)
    if label == "전화번호":
        return RE_PHONE.sub(lambda m: m.group(0)[:3] + "-****-" + m.group(0)[-4:], piece)
    if label == "이메일":
        m = RE_EMAIL.match(piece)
        if m:
            return m.group(1)[0] + "***@" + m.group(2)
        return piece
    if label == "카드번호":
        return RE_CARD.sub(lambda m: f"{m.group(0)[:4]}-****-****-{m.group(0)[-4:]}", piece)
    return piece

# =========================
# 공개 API
# =========================
def run_masking_pipeline(raw_text: str) -> Tuple[str, Dict[str, int], bool]:
    """
    - 입력: 원본 텍스트
    - 출력: (마스킹된 텍스트, counts 딕셔너리, has_pii bool)
    """
    text = raw_text if isinstance(raw_text, str) else str(raw_text)

    # 1) NER로 엔티티 후보 추출 → 우선 치환
    masked = text
    ner_counts = {"email": 0, "rrn": 0, "phone": 0, "card": 0, "name": 0}
    if USE_NER:
        tagged = _ner_predict(text)
        ents = _merge_entities(tagged)
        seen = set()
        for original, label in ents:
            if not original or original in seen:
                continue
            masked_piece = _mask_entity(original, label)
            masked = masked.replace(original, masked_piece, 1)
            seen.add(original)
            if label == "이메일":     ner_counts["email"] += 1
            elif label == "주민번호": ner_counts["rrn"]   += 1
            elif label == "전화번호": ner_counts["phone"] += 1
            elif label == "카드번호": ner_counts["card"]  += 1
            elif label == "이름":     ner_counts["name"]  += 1

    # 2) 정규식 보완 마스킹
    masked = _regex_mask(masked)

    # 3) 카운트 병합
    rx = _regex_counts(text)
    counts = {
        "email": max(rx["email"], ner_counts["email"]),
        "rrn":   max(rx["rrn"],   ner_counts["rrn"]),
        "phone": max(rx["phone"], ner_counts["phone"]),
        "card":  max(rx["card"],  ner_counts["card"]),
        "name":  max(rx["name"],  ner_counts["name"]),
    }

    has_pii = any(v > 0 for v in counts.values())
    return masked, counts, has_pii