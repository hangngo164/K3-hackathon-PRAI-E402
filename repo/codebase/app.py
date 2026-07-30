"""CP2 prototype: upload slides, select text blocks, and complete a mock flow.

Run with: streamlit run app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from core.ingest import build_document
from ui.panels import show_panels
from ui.state import init_state, open_document
from ui.viewer import show_viewer

HERE = Path(__file__).resolve().parent

st.set_page_config(page_title="Trợ lý Ôn Slide", layout="wide", initial_sidebar_state="expanded")


def _load_settings() -> None:
    """Make local and Streamlit-hosted secrets available to the later CP3 core."""

    try:
        from dotenv import load_dotenv

        load_dotenv(HERE / ".env")
    except ImportError:
        pass

    for key in ("OPENAI_API_KEY", "OPENAI_MODEL_FAST", "OPENAI_MODEL_MAIN"):
        try:
            if key in st.secrets and not os.getenv(key):
                os.environ[key] = str(st.secrets[key])
        except Exception:  # No secrets file is a normal local-development state.
            pass


@st.cache_data(show_spinner="Đang đọc và render slide...")
def _load_document(file_bytes: bytes, source_name: str, dpi: int):
    return build_document(file_bytes, source_name, dpi)


_load_settings()
init_state()

st.title("Trợ lý Ôn Slide")
st.caption("CP2: flow bấm được với dữ liệu mock. AI sẽ được tích hợp ở CP3.")

with st.sidebar:
    st.header("Tài liệu")
    uploaded = st.file_uploader("Nạp slide", type=["pdf", "ppt", "pptx"])
    dpi = int(os.getenv("PAGE_DPI", "110"))
    st.caption(f"Nhận PDF, PPTX, PPT. Render ở {dpi} DPI.")

if uploaded is None:
    st.info("Nạp một file PDF, PPTX hoặc PPT để bắt đầu ôn slide.")
    st.stop()

try:
    document = _load_document(uploaded.getvalue(), uploaded.name, dpi)
except (OSError, ValueError) as exc:
    st.error(str(exc))
    st.stop()
open_document(document.doc_hash)

with st.sidebar:
    st.success(f"Đã nạp {document.source_name}")
    st.caption(f"{len(document.pages)} trang · {sum(len(page.blocks) for page in document.pages)} khối văn bản")
    st.divider()
    st.caption("PPT/PPTX ưu tiên chuyển bằng Microsoft PowerPoint để giữ layout. Nếu không có Office, app dùng LibreOffice hoặc bản xem text PPTX.")

viewer_column, panel_column = st.columns([3, 2], gap="large")
with viewer_column:
    page, chosen_ids = show_viewer(document, dpi)
with panel_column:
    show_panels(document, page, chosen_ids)
