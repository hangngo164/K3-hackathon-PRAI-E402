"""Viewer: ảnh trang + overlay vàng + block picker + điều hướng.

Thiết kế "bôi đen" hai tầng: ARCHITECHTURE.md §7. Không gọi AI.

Tầng 1 (đang dùng, không cần JS): chọn khối văn bản => vẽ overlay vàng lên đúng
bbox trên ảnh trang. Anchor thu được GIỐNG HỆT thứ selection thật cho, nên nâng
cấp Tầng 2 (custom component bắt getSelection) không phải sửa core/.

TODO(CP2): bọc @st.fragment để lật trang / tick khối không kéo cả trang rerun.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.config import settings
from core.models import Document
from core.render import draw_highlight, pdf_to_px

from . import state


def show_viewer(doc: Document) -> None:
    page_no = state.get_page_no()
    page = doc.page(page_no)
    if page is None:
        st.warning(f"Không có trang {page_no} trong tài liệu.")
        return

    st.subheader(f"Trang {page_no}/{len(doc.pages)} — {doc.source_name}")

    selected = state.get_selected_blocks()
    dpi = settings().page_dpi
    if selected:
        boxes = [pdf_to_px(b.bbox, dpi) for b in page.blocks if b.block_id in selected]
        highlighted = Path(page.png_path).with_name(Path(page.png_path).stem + "_hl.png")
        draw_highlight(page.png_path, boxes, highlighted)
        st.image(str(highlighted), use_container_width=True)
    else:
        st.image(page.png_path, use_container_width=True)

    nav_prev, nav_next = st.columns(2)
    with nav_prev:
        if st.button("◀ Trang trước", disabled=page_no <= 1, use_container_width=True):
            state.set_page_no(page_no - 1)
            state.clear_selection()  # block_id gắn với một trang cụ thể
            st.rerun()
    with nav_next:
        if st.button("Trang sau ▶", disabled=page_no >= len(doc.pages), use_container_width=True):
            state.set_page_no(page_no + 1)
            state.clear_selection()
            st.rerun()

    if page.char_count < settings().min_chars_per_page:
        st.caption(
            f"Trang này chỉ có {page.char_count} ký tự đọc được — chủ yếu là hình. "
            "Tóm tắt sẽ từ chối thay vì đoán."
        )
        return

    st.write("**Bôi đen:** chọn khối văn bản cần ôn")
    labels = {b.block_id: f"{b.block_id} · {b.text[:60].replace(chr(10), ' ')}" for b in page.blocks}
    chosen = st.multiselect(
        "Khối văn bản trên trang này",
        options=list(labels.keys()),
        default=[b for b in selected if b in labels],
        format_func=lambda bid: labels[bid],
        label_visibility="collapsed",
    )
    if chosen != selected:
        state.set_selected_blocks(chosen)
        st.rerun()


def goto(page_no: int, block_ids: list[str] | None = None) -> None:
    """Nhảy tới nguồn (F2.5) — dùng bởi nút "xem chỗ này" trên bullet/câu hỏi."""
    state.set_page_no(page_no)
    state.set_selected_blocks(block_ids or [])
