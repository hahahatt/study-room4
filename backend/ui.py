# backend/ui.py
from __future__ import annotations
from pathlib import Path
import base64
import streamlit as st

def _find_logo_path() -> str | None:
    here = Path(__file__).resolve()
    candidates = [
        Path("streamlit") / "logo.png",           # CWD 기준
        here.parents[1] / "streamlit" / "logo.png",
        here.parents[2] / "streamlit" / "logo.png",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None

@st.cache_data(show_spinner=False)
def _logo_b64(logo_path: str) -> str:
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def show_logo(max_width: int = 160, pad: int = 2, compact: bool = True):
    """
    모든 페이지 최상단 중앙에 로고 표시.
    - max_width: 로고 최대 너비(px)
    - pad: 로고 위/아래 여백(px) — 기본 2px로 매우 촘촘
    - compact: True면 스트림릿 기본 상단 여백(헤더/메인 패딩)을 최대한 제거
    """
    path = _find_logo_path()
    if not path:
        return
    b64 = _logo_b64(path)

    compact_css = ""
    if compact:
        compact_css = """
        /* Streamlit 기본 상단 여백 최소화 */
        [data-testid="stAppViewContainer"] > .main { padding-top: 0rem; }
        .block-container { padding-top: 0.25rem; }
        /* 헤더 바의 기본 높이를 없애 여백 제거 (메뉴를 쓰지 않으면 추천) */
        [data-testid="stHeader"] { height: 0px; background: transparent; }
        """

    st.markdown(
        f"""
        <style>
        {compact_css}
        ._top_logo_wrap {{
            width: 100%;
            display: block;
            text-align: center;
            margin: {pad}px 0 {pad}px 0;
        }}
        ._top_logo_wrap img {{
            display: block;
            margin-left: auto;
            margin-right: auto;
            max-width: {max_width}px;
            width: 100%;
            height: auto;
        }}
        </style>
        <div class="_top_logo_wrap">
            <img src="data:image/png;base64,{b64}" alt="logo">
        </div>
        """,
        unsafe_allow_html=True,
    )
