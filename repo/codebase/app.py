"""Entrypoint Streamlit — chỉ layout + điều phối, không chứa logic nghiệp vụ.

Layout theo ARCHITECHTURE.md §16: st.columns([3, 2]) — trái viewer, phải panel.
"""

from __future__ import annotations

import os

import streamlit as st

# Đẩy st.secrets vào os.environ TRƯỚC khi import core/ — core không được import
# streamlit (STRUCTURE.md §4), nên nó chỉ đọc được biến môi trường.
try:
    for _key in ("OPENAI_API_KEY", "OPENAI_MODEL_FAST", "OPENAI_MODEL_MAIN"):
        if _key in st.secrets:
            os.environ.setdefault(_key, str(st.secrets[_key]))
except Exception:
    pass  # không có .streamlit/secrets.toml thì dùng .env, không phải lỗi

from core import ingest  # noqa: E402
from core.errors import AppError  # noqa: E402
from ui import panel_quiz, panel_summary, sidebar, state, viewer  # noqa: E402

st.set_page_config(page_title="Trợ lý Ôn Slide", layout="wide")

state.initialize_session_state()
sidebar.show_sidebar()

st.title("Trợ lý Ôn Slide")

uploaded = state.get_uploaded_file()
if uploaded is None:
    st.info("Nạp một file slide (PDF, hoặc PPTX nếu máy có LibreOffice) để bắt đầu.")
    st.stop()


@st.cache_data(show_spinner=False)
def _load_document(data: bytes, source_name: str):
    """Cache theo nội dung file: Streamlit rerun mỗi tương tác, không parse lại."""
    return ingest.ingest(data, source_name)


try:
    with st.spinner("Đang xử lý tài liệu…"):
        # getvalue() chứ không read(): read() ở rerun sau trả b"" vì con trỏ ở EOF
        doc = _load_document(uploaded.getvalue(), uploaded.name)
except AppError as exc:
    st.error(exc.user_message)
    st.stop()

state.set_doc_hash(doc.doc_hash)

col_view, col_panel = st.columns([3, 2])

with col_view:
    viewer.show_viewer(doc)

with col_panel:
    tab_summary, tab_quiz = st.tabs(["Tóm tắt", "Quiz"])
    with tab_summary:
        panel_summary.show_tab(doc)
    with tab_quiz:
        panel_quiz.show_tab(doc)
