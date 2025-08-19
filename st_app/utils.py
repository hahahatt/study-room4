import os, re, time, io, hashlib
import pandas as pd
from typing import Dict, List

LOG_PATH = os.path.join(os.path.dirname(__file__), "audit_log.csv")

DEFAULT_PATTERNS: Dict[str, str] = {
    "주민등록번호": r"\b\d{6}-\d{7}\b",
    "이메일": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "전화번호": r"\b01[016789]-?\d{3,4}-?\d{4}\b",
}

DEFAULT_POLICIES = {
    "block_if_rrn": True,
    "warn_if_email": True,
    "max_files": 10,
    "max_total_mb": 5.0,
    "url_black_keywords": ["bit.ly", "tinyurl", "ipfs", "rawgithub"],
    "url_white_domains": ["company.co.kr", "intra.company.local"],
}

def get_patterns(session_state) -> Dict[str, str]:
    if "patterns" not in session_state:
        session_state.patterns = DEFAULT_PATTERNS.copy()
    return session_state.patterns

def get_policies(session_state) -> Dict[str, str]:
    if "policies" not in session_state:
        session_state.policies = DEFAULT_POLICIES.copy()
    return session_state.policies

def mask_text(text: str, patterns: Dict[str, str]) -> str:
    masked = text
    for name, pat in patterns.items():
        if name == "이메일":
            masked = re.sub(pat, lambda m: m.group(0).split("@")[0][:2] + "***@***", masked)
        elif name == "주민등록번호":
            masked = re.sub(pat, "******-*******", masked)
        elif name == "전화번호":
            masked = re.sub(pat, "***-****-****", masked)
        else:
            masked = re.sub(pat, "***", masked)
    return masked

def highlight_html(text: str, patterns: Dict[str, str]) -> str:
    html = text
    colors = {
        "주민등록번호": "#fff3cd",  # 연노랑
        "이메일": "#e0f7fa",       # 연하늘
        "전화번호": "#fce4ec",     # 연핑크
    }
    for name, pat in patterns.items():
        color = colors.get(name, "#e8eaf6")
        html = re.sub(pat, lambda m: f"<mark style='background:{color}'>{m.group(0)}</mark>", html)
    return f"<div style='white-space:pre-wrap'>{html}</div>"

def log_detection(filename: str, counts: Dict[str, int]):
    row = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "filename": filename,
    }
    row.update({k: int(v) for k, v in counts.items()})
    df = pd.DataFrame([row])
    if os.path.exists(LOG_PATH):
        old = pd.read_csv(LOG_PATH)
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(LOG_PATH, index=False)

def read_log() -> pd.DataFrame:
    if os.path.exists(LOG_PATH):
        try:
            df = pd.read_csv(LOG_PATH)
            if "ts" in df.columns:
                df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=["ts","filename","주민등록번호","이메일","전화번호"])

def bytes_from_text(s: str) -> io.BytesIO:
    return io.BytesIO(s.encode("utf-8"))

URL_REGEX = r"https?://[^\s)<>\"']+"

def extract_urls(text: str) -> List[str]:
    return re.findall(URL_REGEX, text)

def classify_urls(urls: List[str], policies: Dict[str, str]):
    bad = []
    ok = []
    for u in urls:
        if any(bad_kw.lower() in u.lower() for bad_kw in policies["url_black_keywords"]):
            bad.append(u)
        else:
            ok.append(u)
    return ok, bad

def sha256_short(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:10]
