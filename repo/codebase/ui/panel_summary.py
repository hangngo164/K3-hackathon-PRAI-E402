"""Tab Tóm tắt: chọn scope, hiện bullet có neo trang, nút "xem chỗ này".

Tính năng F1.1-F1.5 (FEATURE.md §3). Không tự gọi model — gọi qua core.summarize.
TODO(CP3): nối vào core.summarize.summarize() và hiện bullet + not_covered + confidence
           (HAX G2/G10 — người dùng cần biết phần nào hệ thống không đọc được).
"""

from __future__ import annotations

import streamlit as st

from core import scope as scope_lib
from core.errors import AppError
from core.models import Document

from . import state


def show_tab(doc: Document) -> None:
    scope = state.current_scope()
    st.caption(f"Phạm vi hiện tại: **{scope}**" + (" (đoạn bôi đen)" if scope == "selection" else ""))

    try:
        ctx = scope_lib.resolve(
            doc,
            scope,
            target_id=str(state.get_page_no()),
            selection_block_ids=state.get_selected_blocks(),
        )
    except AppError as exc:
        # Lớp ① không đủ căn cứ / lớp ② mơ hồ — nói thật, không đoán
        st.warning(exc.user_message)
        return

    st.caption(f"{len(ctx.text.split())} từ · ~{ctx.est_tokens} token · chiến lược: {ctx.strategy}")
    st.info("TODO(CP3): tóm tắt AI chưa nối. Phần cắt scope và neo nguồn đã chạy thật.")
    with st.expander("Xem văn bản sẽ gửi cho model"):
        st.text(ctx.text[:2000])
        if ctx.context_text:
            st.caption("Ngữ cảnh lân cận (không tóm tắt vào):")
            st.text(ctx.context_text[:500])
