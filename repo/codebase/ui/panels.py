"""CP2 mock result panels.  CP3 will replace the generators with real AI calls."""

from __future__ import annotations

import streamlit as st

from core.models import Block, Document, Page


def show_panels(document: Document, page: Page, chosen_ids: set[str]) -> None:
    """Show the clickable mock summary and quiz portions of the main flow."""

    selected_blocks = [block for block in page.blocks if block.block_id in chosen_ids]
    summary_tab, quiz_tab = st.tabs(["Tóm tắt", "Quiz"])

    with summary_tab:
        st.caption("Dữ liệu mock cho CP2. CP3 sẽ thay bằng lời gọi AI có kiểm chứng nguồn.")
        if st.button("Tóm tắt đoạn này", use_container_width=True, key="mock_summary_button"):
            if not selected_blocks:
                st.warning("Chọn ít nhất một khối nội dung trước.")
            else:
                st.session_state.mock_summary = _make_summary(page.page_no, selected_blocks)

        summary = st.session_state.mock_summary
        if summary and summary["doc_hash"] == document.doc_hash and summary["page_no"] == page.page_no:
            st.subheader("Tóm tắt demo")
            st.write(summary["tldr"])
            for bullet in summary["bullets"]:
                st.markdown(f"- {bullet}")
            st.caption(f"Nguồn mock: [trang {page.page_no}]")

    with quiz_tab:
        st.caption("Dữ liệu mock cho CP2. Không có câu hỏi nào được tạo bởi AI ở mốc này.")
        if st.button("Tạo quiz từ đoạn này", use_container_width=True, key="mock_quiz_button"):
            if not selected_blocks:
                st.warning("Chọn ít nhất một khối nội dung trước.")
            else:
                st.session_state.mock_quiz = _make_quiz(document.doc_hash, page.page_no, selected_blocks)
                st.session_state.quiz_scored = False

        quiz = st.session_state.mock_quiz
        if quiz and quiz["doc_hash"] == document.doc_hash and quiz["page_no"] == page.page_no:
            st.subheader("Quiz demo")
            for item in quiz["items"]:
                st.radio(item["question"], item["choices"], index=None, key=f"answer:{item['id']}")
                st.caption(f"Nguồn mock: [trang {page.page_no}]")
            if st.button("Chấm bài", use_container_width=True, key="score_mock_quiz"):
                st.session_state.quiz_scored = True

            if st.session_state.quiz_scored:
                score = sum(st.session_state.get(f"answer:{item['id']}") == item["answer"] for item in quiz["items"])
                st.success(f"Kết quả demo: {score}/{len(quiz['items'])}. CP3 sẽ hiển thị giải thích và neo nguồn thật.")


def _make_summary(page_no: int, blocks: list[Block]) -> dict[str, object]:
    excerpts = [_excerpt(block.text) for block in blocks]
    return {
        "doc_hash": st.session_state.active_doc_hash,
        "page_no": page_no,
        "tldr": "Đây là bản tóm tắt mock của các khối bạn đã chọn để kiểm tra flow CP2.",
        "bullets": [f"Ý {index + 1}: {excerpt}" for index, excerpt in enumerate(excerpts[:3])],
    }


def _make_quiz(doc_hash: str, page_no: int, blocks: list[Block]) -> dict[str, object]:
    excerpts = [_excerpt(block.text) for block in blocks] or ["Nội dung đã chọn"]
    items = []
    for index in range(5):
        excerpt = excerpts[index % len(excerpts)]
        items.append(
            {
                "id": f"{doc_hash}:{page_no}:{index}",
                "question": f"Câu {index + 1}. Nội dung nào thuộc đoạn bạn đã chọn?",
                "choices": [excerpt, "Một nội dung không có trong slide", "Một suy đoán ngoài phạm vi", "Không đủ thông tin để kết luận"],
                "answer": excerpt,
            }
        )
    return {"doc_hash": doc_hash, "page_no": page_no, "items": items}


def _excerpt(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:110] + ("..." if len(compact) > 110 else "")
