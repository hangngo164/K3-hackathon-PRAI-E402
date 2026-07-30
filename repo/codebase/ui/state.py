"""Khai báo khoá session_state + get/set.

Bảng khoá: ARCHITECHTURE.md §13. Không gọi core trực tiếp — chỉ giữ trạng thái.

Streamlit chạy lại TOÀN BỘ script sau mỗi tương tác. Mọi thứ đắt (parse, render,
gọi AI) phải nằm trong cache hoặc session_state.
Cache trên đĩa là nguồn sự thật; session_state chỉ là bản sao cho phiên.
"""

from __future__ import annotations

import streamlit as st

DEFAULTS = {
    "doc_hash": None,
    "page_no": 1,
    "selected_block_ids": [],
    "scope": "page",
    "target_id": None,
    "results": {},          # {(scope, target_id, kind): payload}
    "pending": False,       # job đang chạy => khoá nút, tránh double-submit khi rerun
    "cost": {"calls": 0, "tokens": 0},
    "uploaded_file": None,
}


def initialize_session_state() -> None:
    """Gọi một lần ở đầu app.py."""
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_uploaded_file(uploaded_file) -> None:
    st.session_state.uploaded_file = uploaded_file


def get_uploaded_file():
    return st.session_state.uploaded_file


def set_doc_hash(doc_hash: str) -> None:
    st.session_state.doc_hash = doc_hash


def get_doc_hash() -> str | None:
    return st.session_state.doc_hash


def set_page_no(page_no: int) -> None:
    st.session_state.page_no = page_no


def get_page_no() -> int:
    return st.session_state.page_no


def set_selected_blocks(block_ids: list[str]) -> None:
    st.session_state.selected_block_ids = block_ids


def get_selected_blocks() -> list[str]:
    return st.session_state.selected_block_ids


def clear_selection() -> None:
    """Đổi trang thì xoá selection cũ — block_id gắn với một trang cụ thể."""
    st.session_state.selected_block_ids = []


def current_scope() -> str:
    """Có khối đang bôi đen => scope 'selection', ngược lại => 'page'."""
    return "selection" if st.session_state.selected_block_ids else "page"


def set_result(key: tuple, value) -> None:
    st.session_state.results[key] = value


def get_result(key: tuple):
    return st.session_state.results.get(key)
