import re
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from pathlib import Path
from functools import lru_cache

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


BASE_DIR = Path(__file__).resolve().parent          # .../backend/email
BACKEND_DIR = BASE_DIR.parent                       # .../backend
MODEL_DIR = BACKEND_DIR / "ner_model"               #

MODEL_PATH = MODEL_DIR.resolve()

tokenizer = AutoTokenizer.from_pretrained(str(MODEL_PATH), local_files_only=True)
model = AutoModelForTokenClassification.from_pretrained(str(MODEL_PATH), local_files_only=True)
model.eval()

# ─────────────────────────────
# 🔍 NER 예측
# ─────────────────────────────
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

# ─────────────────────────────
# 🧩 엔터티 병합
# ─────────────────────────────
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

# ─────────────────────────────
# 🔒 개별 엔터티 마스킹
# ─────────────────────────────
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

# ─────────────────────────────
# 🔍 정규표현식 기반 마스킹 보완
# ─────────────────────────────
def regex_based_mask(text):
    # 주민번호
    text = re.sub(r"\d{6}-\d{7}", lambda m: m.group(0)[:6] + "-*******", text)

    # 전화번호
    phone_patterns = [
        r"\b01[016789]-?\d{3,4}-?\d{4}\b",
        r"\b\d{2,3}-\d{3,4}-\d{4}\b",
        r"\(\d{2,3}\)\s?\d{3,4}-\d{4}\b"
    ]
    for p in phone_patterns:
        text = re.sub(p, lambda m: m.group(0)[:3] + "-****-" + m.group(0)[-4:], text)

    # 이메일
    text = re.sub(r"\b([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
                  lambda m: m.group(1)[0] + "***@" + m.group(2), text)

    # 카드번호
    text = re.sub(r"\b(\d{4})-(\d{4})-(\d{4})-(\d{4})\b",
                  lambda m: f"{m.group(1)}-****-****-{m.group(4)}", text)

    # 지번 주소
    text = re.sub(r"([가-힣]{2,}(시|도)\s?[가-힣]{1,}(구|군|시)).*",
                  lambda m: m.group(1) + " ****", text)

    # 도로명 주소 
    text = re.sub(
        r"([가-힣]{2,}(시|도)\s*[가-힣0-9\-]+(로|길|대로)\s*\d{1,4}(번?길)?(\s*\d{0,4})?)",
        lambda m: m.group(1).split()[0] + " ****",
        text
    )

    # 계좌번호: 3-2-6 형식 또는 숫자만 (10~14자리)
    text = re.sub(
        r"\b\d{2,4}-\d{2,4}-\d{2,6}\b",
        lambda m: m.group(0)[:4] + "-****-" + m.group(0)[-4:],
        text
    )
    text = re.sub(
        r"\b\d{10,14}\b",
        lambda m: m.group(0)[:4] + "****" + m.group(0)[-4:],
        text
    )

    return text

# ─────────────────────────────
# 🔒 전체 마스킹 적용
# ─────────────────────────────
def mask_text(text):
    tagged = ner_predict(text)
    entities = merge_entities(tagged)
    masked = text
    offset = 0
    for word, label in entities:
        if not word.strip():
            continue
        start = masked.find(word, offset)
        if start == -1:
            continue
        end = start + len(word)
        masked_word = mask_entity(word, label)
        masked = masked[:start] + masked_word + masked[end:]
        offset = start + len(masked_word)
    return regex_based_mask(masked)


def contains_sensitive_keywords(text, keywords):
    return any(k in text for k in keywords)
