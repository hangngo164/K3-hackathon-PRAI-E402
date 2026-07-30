"""Quiz Mode: bảng làm bài chiếm chỗ của slide viewer, chat vẫn ở bên cạnh.

Không sinh quiz và không chọn phạm vi — bộ câu hỏi đến từ một lượt chat, và
`app/chat.py` gọi `state.open_quiz()` để mở bảng này.

Bốn thứ ở đây giữ cho quiz là công cụ tự-phát-hiện-chỗ-hổng chứ không phải một
danh sách chữ:
  · mỗi câu có `[trang N]` bấm được — điều kiện để được phép hiển thị câu do AI sinh
  · chấm xong tổng kết theo TRANG cần ôn lại, không chỉ đếm điểm
  · nói thật số câu thực tế khi verify loại bớt ("4/5 câu có căn cứ")
  · 👎 mở "sai chỗ nào?" và ghi lại — mỗi phản hồi là một ứng viên case cho golden set

Bấm "xem chỗ này" thoát về Normal Mode để mở đúng trang nguồn, và đáp án đã chọn
vẫn còn — xem `state.goto()`.
"""

from __future__ import annotations

from collections import Counter

import streamlit as st

from agent_core.log import trace
from agent_core.models import Document

from . import state, viewer

_FEEDBACK_REASONS = [
    "sai kiến thức", "nhiều đáp án đúng", "câu hỏi vô nghĩa",
    "không có trong slide", "quá dễ",
]


def show_quiz(doc: Document) -> None:
    payload = state.get_active_quiz()
    if not payload:
        # Không nên xảy ra: main.py chỉ vào Quiz Mode khi có bộ quiz. Tự chữa thay
        # vì để màn hình trống, vì mất bộ quiz giữa buổi demo là mất cả đường lui.
        state.close_quiz()
        st.rerun()
        return

    items = payload.get("items") or []
    meta = payload.get("_meta") or {}

    header_col, close_col = st.columns([3, 1])
    with header_col:
        st.subheader(f"Quiz — {meta.get('scope_label', doc.source_name)}")
    with close_col:
        if st.button("✕ Đóng Quiz", width="stretch", key="quiz-close-top"):
            state.close_quiz()
            st.rerun()

    st.warning(
        "Câu hỏi do AI sinh từ slide của bạn — kiểm trích dẫn nếu thấy lạ.",
        icon="⚠️",
    )
    for warning in meta.get("warnings") or []:
        st.caption(f"⚠ {warning}")

    graded = state.is_quiz_graded()
    answers = state.quiz_answers()

    # `run` vào key của mọi widget bên dưới: xem `state.open_quiz()` để biết vì
    # sao thiếu nó thì bộ quiz mới hiện sẵn đáp án của bộ cũ.
    run = state.quiz_run()
    for index, item in enumerate(items):
        _render_item(index, item, graded, answers, run)

    if not graded:
        if st.button("Nộp bài", type="primary", disabled=len(answers) < len(items)):
            state.set_quiz_graded(True)
            st.rerun()
        if len(answers) < len(items):
            st.caption(f"Đã trả lời {len(answers)}/{len(items)} câu.")
        return

    _summary(items, answers, doc)
    again_col, done_col = st.columns(2)
    with again_col:
        if st.button("Làm lại bộ này", width="stretch"):
            state.reset_quiz()
            st.rerun()
    with done_col:
        if st.button("Xong — về slide", type="primary", width="stretch"):
            state.close_quiz()
            st.rerun()


def _render_item(index: int, item: dict, graded: bool, answers: dict, run: int) -> None:
    item_id = item.get("item_id") or f"q{index + 1}"
    widget = f"{run}-{item_id}"  # duy nhất theo từng BỘ, không chỉ theo từng câu
    options = item.get("options") or []
    anchor = item.get("anchor") or {}
    page_no = int(anchor.get("page_no") or 0)

    st.markdown(f"**Câu {index + 1}.** {item.get('stem', '')}")

    if options:
        chosen = st.radio(
            "Chọn đáp án",
            options=list(range(len(options))),
            format_func=lambda i: options[i],
            index=answers.get(item_id),
            key=f"quiz-{widget}",
            disabled=graded,
            label_visibility="collapsed",
        )
        if chosen is not None and not graded:
            state.set_quiz_answer(item_id, int(chosen))
    else:
        typed = st.text_input("Trả lời ngắn", key=f"quiz-text-{widget}", disabled=graded)
        if typed and not graded:
            state.set_quiz_answer(item_id, 0)

    if not graded:
        st.caption(f"độ khó: {item.get('difficulty', '?')}")
        st.divider()
        return

    correct_index = int(item.get("answer_index", -1))
    picked = answers.get(item_id)
    is_correct = picked == correct_index if options else None

    if is_correct is True:
        st.success(f"Đúng — {item.get('answer_text', '')}")
    elif is_correct is False:
        st.error(f"Chưa đúng. Đáp án: {item.get('answer_text', '')}")
    else:
        st.info(f"Đáp án tham khảo: {item.get('answer_text', '')}")

    st.caption(item.get("explanation", ""))
    if anchor.get("quote"):
        st.caption(f"nguồn: “{anchor['quote'][:160]}”")

    cite_col, up_col, down_col = st.columns([2, 1, 1])
    with cite_col:
        if page_no:
            viewer.jump_button(f"↪ trang {page_no}", page_no, key=f"quiz-jump-{widget}")
    with up_col:
        if st.button("👍", key=f"up-{widget}"):
            trace("feedback", item_id=item_id, vote="up", stem=item.get("stem", "")[:120])
            st.toast("Đã ghi nhận.")
    with down_col:
        if st.button("👎", key=f"down-{widget}"):
            st.session_state[f"show-fb-{widget}"] = True

    if st.session_state.get(f"show-fb-{widget}"):
        reason = st.radio("Sai chỗ nào?", _FEEDBACK_REASONS,
                          key=f"fb-{widget}", horizontal=True)
        if st.button("Gửi", key=f"fb-send-{widget}"):
            # Ghi vào cùng trace với mọi lời gọi AI: mỗi 👎 là một ứng viên case
            # cho golden set, thu ngay trong flow thay vì phỏng vấn lại sau.
            trace("feedback", item_id=item_id, vote="down", reason=reason,
                  stem=item.get("stem", "")[:120], anchor_page=page_no)
            st.session_state[f"show-fb-{widget}"] = False
            st.toast("Đã ghi nhận. Cảm ơn bạn.")

    st.divider()


def _summary(items: list[dict], answers: dict, doc: Document) -> None:
    """Tổng kết theo TRANG cần ôn lại — đây mới là "kết quả" người dùng cần.

    Đếm điểm thì ai cũng làm được; chỉ đúng chỗ hổng theo trang mới là thứ giúp
    người học biết mở lại slide nào.
    """
    wrong_pages: Counter = Counter()
    correct = 0
    for item in items:
        options = item.get("options") or []
        if not options:
            continue
        if answers.get(item.get("item_id")) == int(item.get("answer_index", -1)):
            correct += 1
        else:
            page_no = int((item.get("anchor") or {}).get("page_no") or 0)
            if page_no:
                wrong_pages[page_no] += 1

    scored = len([i for i in items if i.get("options")])
    st.markdown(f"### Bạn đúng {correct}/{scored}")

    if not wrong_pages:
        st.success("Không câu nào sai — phần này bạn nắm được.")
        return

    lines = []
    for page_no, count in wrong_pages.most_common():
        page = doc.page(page_no)
        title = next((b.text.split("\n")[0][:60] for b in (page.blocks if page else [])
                      if b.is_title_like), "")
        lines.append(f"- **trang {page_no}**{f' — {title}' if title else ''}: {count} câu sai")
    st.warning("Nên ôn lại:\n" + "\n".join(lines))

    top_page = wrong_pages.most_common(1)[0][0]
    viewer.jump_button(f"↪ mở trang {top_page}", top_page, key="quiz-summary-jump")
