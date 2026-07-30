"""PDF page navigation and selectable text-block viewer."""

from __future__ import annotations

import streamlit as st

from core.models import Document, Page
from core.render import render_highlights
from ui.state import clear_selection, selected_ids


def show_viewer(document: Document, dpi: int) -> tuple[Page, set[str]]:
    """Render navigation, selectable blocks, and the highlighted page image."""

    page_total = len(document.pages)
    page_no = int(st.session_state.page_no)
    nav_left, nav_center, nav_right = st.columns([1, 2, 1])

    with nav_left:
        if st.button("Trang trước", disabled=page_no == 1, use_container_width=True):
            clear_selection(document.doc_hash)
            st.session_state.page_no = page_no - 1
            st.rerun()
    with nav_center:
        requested_page = st.number_input(
            "Trang",
            min_value=1,
            max_value=page_total,
            value=page_no,
            step=1,
            label_visibility="collapsed",
        )
        if requested_page != page_no:
            clear_selection(document.doc_hash)
            st.session_state.page_no = int(requested_page)
            st.rerun()
        st.caption(f"Trang {page_no}/{page_total}")
    with nav_right:
        if st.button("Trang sau", disabled=page_no == page_total, use_container_width=True):
            clear_selection(document.doc_hash)
            st.session_state.page_no = page_no + 1
            st.rerun()

    page = document.pages[page_no - 1]
    image_col, picker_col = st.columns([3, 2], gap="medium")
    with picker_col:
        st.subheader("Chọn nội dung")
        if not page.blocks:
            st.info("Trang này không có lớp văn bản để chọn.")
        for block in page.blocks:
            label = " ".join(block.text.split())
            label = label[:76] + ("..." if len(label) > 76 else "")
            st.checkbox(label, key=f"selected:{document.doc_hash}:{page_no}:{block.block_id}")

    chosen = selected_ids(document.doc_hash, page_no)
    with image_col:
        highlighted = render_highlights(page.image_png, page.blocks, chosen, dpi)
        st.image(highlighted, use_container_width=True)
        if chosen:
            st.caption(f"Đã chọn {len(chosen)} khối trên trang {page_no}.")
        else:
            st.caption("Chọn khối ở cột bên phải để đánh dấu trên slide.")

    return page, chosen
