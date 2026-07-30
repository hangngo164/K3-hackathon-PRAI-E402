"""Vẽ một bản tóm tắt vào bubble chat. Chỉ hiển thị — không chọn phạm vi, không gọi tool.

Trước refactor đây là một tab có nút bấm và bộ chọn phạm vi riêng. Giờ phạm vi do
`tools/router.py` suy ra từ câu người dùng gõ, nên phần còn lại của file là đúng
thứ đáng giữ: cách trình bày một bản tóm tắt có neo nguồn.

Hai thứ ở đây không phải trang trí:
  · nút "xem chỗ này" trên mỗi bullet — điều kiện để tóm tắt được phép chạy tự động
  · `not_covered` + `confidence` — người dùng phải biết phần nào hệ thống không đọc được
"""

from __future__ import annotations

import streamlit as st

from . import viewer

_CONFIDENCE_BADGE = {"high": "🟢 cao", "medium": "🟡 vừa", "low": "🔴 thấp"}


def render(payload: dict, turn_index: int) -> None:
    """`turn_index` vào key của nút: cùng một bullet ở hai lượt chat là hai nút khác nhau."""
    meta = payload.get("_meta") or {}

    if payload.get("tldr"):
        st.markdown(f"**{payload['tldr']}**")

    for index, bullet in enumerate(payload.get("bullets") or []):
        anchor = bullet.get("anchor") or {}
        page_no = int(anchor.get("page_no") or 0)
        st.markdown(f"- {bullet.get('text', '')}")
        cite_col, quote_col = st.columns([1, 3])
        with cite_col:
            if page_no:
                viewer.jump_button(f"↪ trang {page_no}", page_no,
                                   key=f"sum-jump-{turn_index}-{index}")
        with quote_col:
            if anchor.get("quote"):
                st.caption(f"“{anchor['quote'][:160]}”")

    if payload.get("key_terms"):
        with st.expander("Thuật ngữ"):
            for term in payload["key_terms"]:
                st.markdown(f"**{term.get('term', '')}** — {term.get('meaning', '')}")
                if int(term.get("page_no") or 0):
                    st.caption(f"định nghĩa ở trang {term['page_no']}")

    if payload.get("not_covered"):
        st.warning("**Phần không đọc được:**\n" + "\n".join(
            f"- {item}" for item in payload["not_covered"]
        ))

    for warning in meta.get("warnings") or []:
        st.caption(f"⚠ {warning}")

    confidence = _CONFIDENCE_BADGE.get(payload.get("confidence", ""), payload.get("confidence", ""))
    st.caption(
        f"Độ tin: {confidence} · {meta.get('calls', '?')} lời gọi · "
        f"{'cache' if meta.get('cached') else 'sinh mới'} · "
        f"{meta.get('model', '')} · prompt {meta.get('prompt_version', '')}"
        + (f" · loại {meta['dropped_bullets']} bullet" if meta.get("dropped_bullets") else "")
    )
