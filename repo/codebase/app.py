import os
from pathlib import Path

import streamlit as st

from core import ingest, render, scope, summarize, quiz, cache as cache_lib, llm
from ui import state, sidebar, viewer, panel_summary, panel_quiz, chat

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / ".cache"

st.set_page_config(page_title="Daily Quiz Prototype", layout="wide")

state.initialize_session_state()

sidebar.show_sidebar(CACHE_DIR)

st.title("Daily Quiz — Trợ lý Ôn Slide")

uploaded = state.get_uploaded_file()
if uploaded is None:
    st.info("Hãy upload một file PDF hoặc PPTX để bắt đầu.")
    st.stop()

with st.spinner("Đang xử lý tài liệu…"):
    doc = ingest.load_document(uploaded, CACHE_DIR)

if doc is None:
    st.error("Không thể đọc tài liệu. Vui lòng thử lại với file khác.")
    st.stop()

col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    viewer.show_viewer(doc)

with col2:
    tab1, tab2 = st.tabs(["Tóm tắt", "Quiz"])
    with tab1:
        panel_summary.show_tab(doc)
    with tab2:
        panel_quiz.show_tab(doc)

with col3:
    chat.show_chat(doc)
