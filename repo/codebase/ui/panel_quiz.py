"""Tab Quiz: sinh câu hỏi, làm, chấm, xem giải thích có trích dẫn, 👍👎.

Tính năng F2.1-F2.6 (FEATURE.md §4). Không tự gọi model — gọi qua core.quiz.

TODO(CP3) — bốn thứ không được thiếu khi nối AI:
  · mỗi câu hiện [trang N] bấm được (F2.5) — điều kiện để quiz là AUGMENT
  · chấm xong tổng kết theo trang/mục cần ôn lại (F2.4) — "kết quả" của lát cắt
  · số câu thực tế nói thật khi verify loại item ("4/5 câu có căn cứ")
  · 👎 => "sai chỗ nào?" ghi eval/feedback.jsonl (F2.6, HAX G15)
"""

from __future__ import annotations

import streamlit as st

from core import scope as scope_lib
from core.errors import AppError
from core.models import Document

from . import state


def show_tab(doc: Document) -> None:
    if not state.get_selected_blocks():
        st.warning("Bôi đen ít nhất một khối trên slide rồi mới tạo quiz được.")
        return

    try:
        ctx = scope_lib.resolve(
            doc,
            "selection",
            selection_block_ids=state.get_selected_blocks(),
        )
    except AppError as exc:
        st.warning(exc.user_message)  # lớp ②: đoạn quá ngắn => hỏi lại, không nhồi câu
        return

    n_items = st.radio("Số câu", [3, 5, 8], index=1, horizontal=True)
    st.caption(f"Nguồn: {len(ctx.text.split())} từ · neo được vào {len(ctx.unit_ids) - 1} khối")

    if st.button("Sinh quiz", type="primary", disabled=state.get_result(("pending",)) is True):
        st.info(f"TODO(CP3): core.quiz.generate() chưa nối — sẽ sinh {n_items} câu có trích dẫn.")
