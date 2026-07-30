"""Sidebar: nạp nhiều file · chọn file đang đọc · cây chương/mục · môi trường · chi phí.

Không xử lý file — chỉ nhận từ widget rồi trả về cho `main.py` gọi `agent_core.ingest`.
Đường dẫn cache lấy từ `agent_core.config`, không truyền tay từ `main.py`.
"""

from __future__ import annotations

import streamlit as st

from agent_core import log
from agent_core.config import CACHE_DIR, settings
from agent_core.models import Document

from . import state

_OUTLINE_SOURCE_LABEL = {
    "toc": "mục lục có sẵn trong PDF",
    "heuristic": "tự dò theo slide phân cách",
    "llm": "AI dò từ tiêu đề trang",
    "flat": "không tách được chương/mục",
}


def show_upload() -> list:
    """Ô nạp file. Trả danh sách file đang có trong widget (có thể nhiều)."""
    st.sidebar.title("Tài liệu")
    uploaded = st.sidebar.file_uploader(
        "Nạp slide (PDF / PPTX)",
        type=["pdf", "pptx"],
        accept_multiple_files=True,
        help="Nạp nhiều buổi cùng lúc rồi chọn buổi muốn ôn ở dưới.",
    )
    return uploaded or []


def show_status(documents: dict[str, Document]) -> None:
    """Chọn file đang đọc + cây chương/mục + trạng thái key + chi phí phiên."""
    if documents:
        _document_picker(documents)
        _outline_tree(documents[state.active_doc_hash()])

    st.sidebar.markdown("---")
    _environment()
    _cost()


def _document_picker(documents: dict[str, Document]) -> None:
    """Nhiều file thì hiện danh sách chọn; một file thì chỉ hiện tên, không bắt chọn."""
    registry = state.docs()
    hashes = list(documents)

    if len(hashes) == 1:
        st.sidebar.caption(f"Đang đọc: **{registry[hashes[0]]['name']}**")
        return

    active = state.active_doc_hash()
    chosen = st.sidebar.radio(
        "Đang đọc file nào",
        options=hashes,
        index=hashes.index(active) if active in hashes else 0,
        format_func=lambda h: f"{registry[h]['name']} · {len(documents[h].pages)} trang",
    )
    if chosen != active:
        state.set_active_doc(chosen)
        st.rerun()  # đổi file thì panel bên phải phải vẽ lại theo tài liệu mới


def _outline_tree(doc: Document) -> None:
    """Mục lục để ĐIỀU HƯỚNG. Phạm vi giờ suy ra từ câu người dùng gõ trong chat.

    Vẫn giữ cây này sau khi bỏ bộ chọn phạm vi, vì nó còn hai việc: cho người
    dùng thấy tài liệu có cấu trúc gì (nên hỏi "chương 2" mới có nghĩa), và nhảy
    nhanh tới đầu một chương mà không phải đếm số trang.
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("Mục lục")
    source = _OUTLINE_SOURCE_LABEL.get(doc.outline_source, doc.outline_source)

    if not doc.chapters:
        # Nói rõ lý do thay vì hiện nút bấm vào ra rác: hỏi "tóm tắt chương 2"
        # trên một cấu trúc không có thật thì phạm vi sai mà người dùng không biết.
        st.sidebar.caption(
            f"Tài liệu này {source} — hỏi theo trang, theo khoảng trang, "
            "hoặc toàn bộ tài liệu."
        )
        return

    st.sidebar.caption(f"Cây chương/mục: {source} · bấm để mở trang đầu phần đó")
    for chapter in doc.chapters:
        first, last = chapter.page_range
        if st.sidebar.button(
            f"{chapter.title}  ·  tr.{first}-{last}",
            key=f"goto-{chapter.unit_id}",
            width="stretch",
        ):
            state.goto(first)
            st.rerun()
        for section in chapter.sections:
            s_first, s_last = section.page_range
            if st.sidebar.button(
                f"　› {section.title}  ·  tr.{s_first}-{s_last}",
                key=f"goto-{section.unit_id}",
                width="stretch",
            ):
                state.goto(s_first)
                st.rerun()


def _environment() -> None:
    st.sidebar.subheader("Môi trường")
    problems = settings().problems()
    if problems:
        for problem in problems:
            st.sidebar.warning(problem)
        st.sidebar.caption("Xem slide và lật trang vẫn dùng được; chỉ phần gọi AI bị chặn.")
    else:
        cfg = settings()
        st.sidebar.success(f"API key OK · {cfg.model_fast} / {cfg.model_main}")

    st.session_state.use_llm_outline = st.sidebar.toggle(
        "Dùng AI dò chương/mục khi không tự dò được",
        value=st.session_state.use_llm_outline,
        help="Thêm một lời gọi rẻ lúc nạp file, và chỉ chạy khi PDF không có mục lục "
             "và cũng không dò được bằng hình thức slide.",
    )


def _cost() -> None:
    """Chi phí đọc từ trace trên đĩa, không từ biến đếm trong RAM.

    Lý do: `eval/run.py` chạy ở tiến trình khác cũng cộng vào cùng con số, và
    rerun của Streamlit không làm mất số đã đếm.
    """
    totals = log.session_cost()
    st.sidebar.caption(
        f"Hôm nay: {totals['calls']} lời gọi AI · "
        f"{totals['tokens_in']:,} token vào ({totals['cached_tokens']:,} từ cache) · "
        f"{totals['tokens_out']:,} token ra"
    )
    st.sidebar.caption(f"Cache: {CACHE_DIR}")
