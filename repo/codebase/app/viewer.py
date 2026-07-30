"""Normal Mode: ảnh trang + điều hướng. Không gọi AI.

Trước đây file này còn một block picker để "bôi đen" khối văn bản rồi vẽ overlay
vàng lên ảnh trang. Đã bỏ: phạm vi giờ nói bằng lời trong chat ("tóm tắt trang
6", "chương 2"), nên cái picker chỉ còn là một danh sách checkbox dài chen giữa
slide và phần điều hướng.

Neo nguồn KHÔNG mất theo: mỗi bullet và mỗi câu quiz vẫn mang `anchor` có
`page_no` + `block_ids` + `quote`, `verify.py` vẫn đối chiếu vào `unit_ids`, và
nút "xem chỗ này" vẫn mở đúng trang. Cái mất đúng một thứ: vệt vàng chỉ tận khối
trên ảnh.
"""

from __future__ import annotations

import streamlit as st

from agent_core.config import settings
from agent_core.models import Document

from . import state


def show_viewer(doc: Document) -> None:
    page_no = min(state.get_page_no(), len(doc.pages))
    page = doc.page(page_no)
    if page is None:
        st.warning(f"Không có trang {page_no} trong tài liệu.")
        return

    st.subheader(f"Trang {page_no}/{len(doc.pages)} — {doc.source_name}")
    _navigation(doc, page_no)
    st.image(page.png_path, width="stretch")

    if page.char_count < settings().min_chars_per_page:
        st.caption(
            f"Trang này chỉ có {page.char_count} ký tự đọc được — chủ yếu là hình. "
            "Tóm tắt sẽ từ chối thay vì đoán."
        )


def _navigation(doc: Document, page_no: int) -> None:
    prev_col, jump_col, next_col = st.columns([1, 1, 1])
    with prev_col:
        if st.button("◀ Trang trước", disabled=page_no <= 1, width="stretch"):
            state.set_page_no(page_no - 1)
            st.rerun()
    with jump_col:
        target = st.number_input(
            "Tới trang", min_value=1, max_value=len(doc.pages), value=page_no,
            label_visibility="collapsed",
        )
        if target != page_no:
            state.set_page_no(int(target))
            st.rerun()
    with next_col:
        if st.button("Trang sau ▶", disabled=page_no >= len(doc.pages),
                     width="stretch"):
            state.set_page_no(page_no + 1)
            st.rerun()


def jump_button(label: str, page_no: int, key: str) -> None:
    """Nút "xem chỗ này" dùng chung cho bullet tóm tắt, câu quiz và trích dẫn chat.

    Đây là thứ cho phép tóm tắt được phép chạy tự động: người dùng kiểm được một
    bullet bằng đúng một cú bấm.
    """
    if st.button(label, key=key):
        state.goto(page_no)
        st.rerun()
