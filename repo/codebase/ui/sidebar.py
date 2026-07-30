"""Sidebar: upload · trạng thái môi trường · cost phiên.

Không xử lý file — chỉ nhận file rồi đưa vào session_state; app.py gọi core.ingest.
Đường dẫn cache lấy từ core.config, không truyền tay từ app.py.
TODO(CP4): cây chương/mục (F3.4) khi outline.py dò được thật.
"""

from __future__ import annotations

import streamlit as st

from core.config import CACHE_DIR, settings

from . import state


def show_sidebar() -> None:
    st.sidebar.title("Tài liệu")
    uploaded = st.sidebar.file_uploader("Nạp slide (PDF / PPTX)", type=["pdf", "pptx"])
    if uploaded is not None:
        state.set_uploaded_file(uploaded)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Phiên hiện tại")
    st.sidebar.write(f"Trang: **{state.get_page_no()}**")
    st.sidebar.write(f"Scope: **{state.current_scope()}**")
    selected = state.get_selected_blocks()
    if selected:
        st.sidebar.caption(f"Đang bôi đen {len(selected)} khối: {', '.join(selected)}")
    cost = st.session_state.get("cost", {})
    st.sidebar.caption(f"Lời gọi AI phiên này: {cost.get('calls', 0)} · token: {cost.get('tokens', 0)}")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Môi trường")
    problems = settings().problems()
    if problems:
        for problem in problems:
            st.sidebar.warning(problem)
        st.sidebar.caption("Viewer và bôi đen vẫn dùng được; chỉ phần gọi AI bị chặn.")
    else:
        st.sidebar.success(f"API key OK · model: {settings().model_fast} / {settings().model_main}")
    st.sidebar.caption(f"Cache: {CACHE_DIR}")
