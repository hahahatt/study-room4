# contains_sensitive_keywords 수정
# _load_model_ 추가


import re
import torch
from functools import lru_cache
from transformers import AutoTokenizer, AutoModelForTokenClassification
from pathlib import Path

LABEL_LIST = [
    "O",
    "B-이름", "I-이름",
    "B-주민번호", "I-주민번호",
    "B-전화번호", "I-전화번호",
    "B-이메일", "I-이메일",
    "B-카드번호", "I-카드번호",
    "B-주소", "I-주소"
]

id2label = {i: label for i, label in enumerate(LABEL_LIST)}

# email 폴더 기준 부모가 backend 이므로, backend/ner_model 을 정확히 가리킴
BASE_DIR = Path(__file__).resolve().parent          # .../backend/email
BACKEND_DIR = BASE_DIR.parent                       # .../backend
MODEL_DIR = BACKEND_DIR / "ner_model"               #

MODEL_PATH = MODEL_DIR.resolve()

tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True)
model = AutoModelForTokenClassification.from_pretrained(str(MODEL_PATH), local_files_only=True)
model.eval()


def _is_valid_hf_dir(p: Path) -> bool:
    """허깅페이스 로컬 모델 폴더 최소 요건 확인"""
    if not p or not p.exists() or not p.is_dir():
        return False
    has_config = (p / "config.json").exists()
    has_model = (p / "pytorch_model.bin").exists() or (p / "model.safetensors").exists()
    has_tok   = (p / "tokenizer.json").exists() or (p / "vocab.txt").exists() or (p / "spiece.model").exists()
    return has_config and has_model and has_tok

# NER은 필수 조건 → 폴더가 없거나 불완전하면 명확한 에러로 중단
if not _is_valid_hf_dir(MODEL_DIR):
    raise RuntimeError(
        f"[NER 모델 폴더 오류] '{MODEL_DIR}'에 다음 파일들이 있어야 합니다:\n"
        f"- config.json\n- (pytorch_model.bin | model.safetensors)\n"
        f"- (tokenizer.json | vocab.txt | spiece.model)\n"
        f"ner_model 폴더가 있는지 확인하세요"
    )

@lru_cache(maxsize=1)
def _load_model():
    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = AutoModelForTokenClassification.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model.eval()
    return tokenizer, model


def ner_predict(text):
    tokens = list(text)
    tokenized = tokenizer(tokens, is_split_into_words=True, return_tensors="pt", truncation=True)
    with torch.no_grad():
        output = model(**tokenized)
    preds = output.logits.argmax(dim=-1).squeeze().tolist()
    word_ids = tokenized.word_ids()
    merged = []
    prev_id = None
    for idx, wid in enumerate(word_ids):
        if wid is None or wid == prev_id:
            continue
        merged.append((tokens[wid], id2label[preds[idx]]))
        prev_id = wid
    return merged

def merge_entities(tagged):
    result = []
    tag = None
    buffer = ""
    for char, label in tagged:
        if label.startswith("B-"):
            if tag:
                result.append((buffer, tag))
            tag = label[2:]
            buffer = char
        elif label.startswith("I-") and tag == label[2:]:
            buffer += char
        else:
            if tag:
                result.append((buffer, tag))
            tag, buffer = None, ""
    if tag:
        result.append((buffer, tag))
    return result

def mask_entity(text, label):
    if label == "이름":
        return text[0] + "**" if len(text) >= 2 else text + "*"
    elif label == "주민번호":
        return re.sub(r"\d{6}-\d{7}", lambda m: m.group(0)[:6] + "-*******", text)
    elif label == "전화번호":
        return re.sub(r"\d{2,3}-\d{3,4}-\d{4}", lambda m: m.group(0)[:3] + "-****-" + m.group(0)[-4:], text)
    elif label == "이메일":
        local, _, domain = text.partition("@")
        return local[0] + "***@" + domain
    elif label == "카드번호":
        return re.sub(r"\d{4}-\d{4}-\d{4}-\d{4}", lambda m: f"{m.group(0)[:4]}-****-****-{m.group(0)[-4:]}", text)
    elif label == "주소":
        return re.sub(r"([가-힣]{2,}(시|도)\s?[가-힣]{1,}(구|군|시)).*", lambda m: m.group(1) + " ****", text)
    else:
        return text

def regex_based_mask(text):
    text = re.sub(r"\d{6}-\d{7}", lambda m: m.group(0)[:6] + "-*******", text)
    phone_patterns = [
        r"\b01[016789]-?\d{3,4}-?\d{4}\b",
        r"\b\d{2,3}-\d{3,4}-\d{4}\b",
        r"\(\d{2,3}\)\s?\d{3,4}-\d{4}\b"
    ]
    for p in phone_patterns:
        text = re.sub(p, lambda m: m.group(0)[:3] + "-****-" + m.group(0)[-4:], text)
    text = re.sub(r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
                  lambda m: m.group(1)[0] + "***@" + m.group(2), text)
    text = re.sub(r"\b(\d{4})-(\d{4})-(\d{4})-(\d{4})\b",
                  lambda m: f"{m.group(1)}-****-****-{m.group(4)}", text)
    text = re.sub(r"([가-힣]{2,}(시|도)\s?[가-힣]{1,}(구|군|시)).*",
                  lambda m: m.group(1) + " ****", text)
    return text

def mask_text(text):
    tagged = ner_predict(text)
    entities = merge_entities(tagged)
    masked = text
    for word, label in entities:
        if word.strip():
            masked = masked.replace(word, mask_entity(word, label), 1)
    return regex_based_mask(masked)

def contains_sensitive_keywords(text, keywords):
    low = (text or "").lower()
    return any(k.lower() in low for k in keywords)
    # 원래 형태 : return any(k in text for k in keywords)
