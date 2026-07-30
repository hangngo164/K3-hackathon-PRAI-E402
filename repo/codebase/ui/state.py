"""Khai báo khoá session_state + get/set có kiểm tra.

TODO(CP2). Bảng khoá: ARCHITECHTURE.md §13.
Không gọi core trực tiếp — chỉ giữ trạng thái.

Streamlit chạy lại TOÀN BỘ script sau mỗi tương tác. Mọi thứ đắt (parse, render,
gọi AI) phải nằm trong cache hoặc session_state, không nằm thẳng trong luồng render.
Cache trên đĩa là nguồn sự thật; session_state chỉ là bản sao cho phiên.
"""

from __future__ import annotations

from typing import Any

# Khoá dùng trong st.session_state — không gõ chuỗi tự do ở chỗ khác
DOC_HASH = "doc_hash"
PAGE_NO = "page_no"
SELECTED_BLOCK_IDS = "selected_block_ids"
SCOPE = "scope"
TARGET_ID = "target_id"
RESULTS = "results"  # {(scope, target_id, kind): payload}
PENDING = "pending"  # job đang chạy => khoá nút, tránh double-submit khi rerun
COST = "cost"

DEFAULTS: dict[str, Any] = {
    DOC_HASH: None,
    PAGE_NO: 1,
    SELECTED_BLOCK_IDS: [],
    SCOPE: "page",
    TARGET_ID: None,
    RESULTS: {},
    PENDING: None,
    COST: {"calls": 0, "tokens": 0},
}


def init() -> None:
    """Gọi một lần ở đầu app.py."""
    raise NotImplementedError("TODO(CP2)")


def clear_selection() -> None:
    """Đổi trang thì xoá selection cũ và nói rõ cho người dùng."""
    raise NotImplementedError("TODO(CP2)")
