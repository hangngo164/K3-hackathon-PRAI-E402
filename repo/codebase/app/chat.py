"""Cửa sổ chat — nơi DUY NHẤT người dùng ra yêu cầu.

Không có nút "Tóm tắt", không có nút "Tạo quiz", không có bộ chọn phạm vi. Người
dùng gõ một câu; `tools/router.py` chọn tool và phạm vi; file này chỉ điều phối và
vẽ kết quả.

Ba loại nút vẫn còn, và không cái nào là nút chọn tính năng:
  · "xem chỗ này" — mở đúng trang nguồn của một bullet / câu quiz / trích dẫn
  · lựa chọn cho một câu hỏi làm rõ — trả lời nhanh thay vì gõ lại
  · xác nhận một job lớn — "41 lời gọi, ~26s, chạy nhé?"

Dùng `st.form` chứ không `st.chat_input`: `chat_input` chỉ đặt được ở thân trang
chính hoặc sidebar, mà panel này nằm trong `st.columns`.
"""

from __future__ import annotations

import streamlit as st

from agent_core import scope as scope_lib
from agent_core.errors import AppError, BudgetExceeded
from agent_core.intent import Plan, UIContext
from agent_core.models import Document
from tools import registry, router

from . import panel_summary, state, viewer

# Dưới ngưỡng này thì job xong trong vài giây — chen một câu xác nhận vào chỉ làm
# người dùng phải bấm thêm một lần cho việc họ vừa mới xin.
_CONFIRM_ABOVE_CALLS = 8
_QUEUED_MESSAGE = "_chat_queued_message"

_REFUSAL_HINT = {
    "not_in_document": "Tài liệu này không nói về điều đó.",
    "out_of_scope": "Việc này nằm ngoài phạm vi ôn slide.",
    "too_vague": "Câu hỏi chưa đủ rõ để tìm.",
}


def show_chat(doc: Document, history_height: int = 460) -> None:
    """Lịch sử cuộn trong khung riêng; ô nhập ghim dưới, ngoài khung.

    `st.container(height=...)` tự bật auto-scroll khi bên trong có `st.chat_message`,
    nên lượt mới luôn hiện ra mà không phải kéo tay.

    Mọi việc SINH RA THAY ĐỔI đều chạy ở đầu hàm này, trước khi vẽ bất cứ thứ gì:
    ô nhập và các nút trong bubble đều chỉ xếp hàng một việc rồi `st.rerun()`, và
    lượt chạy sau mới xử. Nhờ vậy `_handle()` chỉ có ĐÚNG MỘT chỗ gọi, và tới lúc
    `app/main.py` vẽ cột trái thì UI mode đã chốt xong.
    """
    # Chạy TRONG cột chat chứ không ở đầu main.py: hai việc này vẽ progress bar,
    # và progress bar phải hiện ở chỗ người dùng đang nhìn.
    _run_confirmed_plan(doc)

    queued = st.session_state.pop(_QUEUED_MESSAGE, "")
    if queued:
        _handle(doc, queued)

    with st.container(height=history_height, border=False):
        _render_history(doc)

    with st.form("chat-form", clear_on_submit=True):
        message = st.text_area(
            "Yêu cầu",
            placeholder="Ví dụ: tóm tắt chương 2 · tạo 5 câu quiz trang này · attention là gì?",
            height=80, label_visibility="collapsed",
        )
        send_col, clear_col = st.columns([3, 1])
        with send_col:
            sent = st.form_submit_button("Gửi", type="primary", width="stretch",
                                         disabled=state.is_pending())
        with clear_col:
            cleared = st.form_submit_button("Xoá hội thoại", width="stretch")

    if cleared:
        state.clear_chat()
        st.rerun()

    if sent and message.strip():
        # Xếp hàng rồi rerun thay vì xử ngay tại đây: lịch sử đã vẽ phía trên nên
        # xử ở đây vẫn phải rerun mới thấy lượt mới — cùng một lượt chạy lại, mà
        # đổi lại `_handle()` chỉ còn một chỗ gọi và luôn chạy trước lúc vẽ.
        _queue(message.strip())


def _queue(message: str) -> None:
    """Xếp một câu vào hàng đợi rồi chạy lại; lượt sau `show_chat()` sẽ xử ở đầu hàm.

    Dùng chung cho ô nhập và cho các nút lựa chọn trong bubble, nên hai đường đó
    đi qua đúng một luồng.
    """
    st.session_state[_QUEUED_MESSAGE] = message
    st.rerun()


# --- Điều phối một lượt ---

def _handle(doc: Document, message: str) -> None:
    history = _history_for_model()
    state.add_chat_turn("user", message)
    state.set_pending_plan(None)  # câu mới huỷ mọi xác nhận đang treo

    try:
        with st.spinner("Đang xác định yêu cầu…"):
            plan = router.route(doc, message, _ui_context(doc), history)
    except AppError as exc:
        state.add_chat_turn("assistant", f"⚠ {exc.user_message}", kind="error")
        return

    _execute(doc, plan)


def _execute(doc: Document, plan: Plan) -> None:
    if plan.kind == "clarify":
        state.add_chat_turn("assistant", plan.question,
                            {"options": plan.options}, kind="clarify")
        return

    if plan.kind == "explain":
        _explain_quiz_item(plan)
        return

    if plan.tool == "ask":
        _run_ask(doc, plan)
        return

    estimate = _job_estimate(doc, plan)
    if estimate is not None:
        _ask_to_confirm(plan, estimate)
        return

    _run_scoped_tool(doc, plan)


def _run_scoped_tool(doc: Document, plan: Plan) -> None:
    if plan.tool == "summarize":
        _run_summarize(doc, plan)
    elif plan.tool == "quiz":
        _run_quiz(doc, plan)


# --- Xác nhận job lớn: báo trước số lời gọi, không đốt 41 lời gọi trong im lặng ---

def _job_estimate(doc: Document, plan: Plan) -> dict | None:
    try:
        estimate = scope_lib.estimate_job(doc, plan.scope, plan.target_id)
    except AppError:
        return None  # phạm vi có vấn đề thì để tool báo bằng thông điệp của nó
    return estimate if estimate["calls"] > _CONFIRM_ABOVE_CALLS else None


def _ask_to_confirm(plan: Plan, estimate: dict) -> None:
    state.set_pending_plan(_plan_as_dict(plan))
    state.add_chat_turn(
        "assistant",
        f"Phạm vi này có {estimate['readable_pages']}/{estimate['pages']} trang đọc được "
        f"→ khoảng {estimate['calls']} lời gọi AI, ~{estimate['seconds']}s. "
        "Chạy lại lần sau sẽ lấy từ cache.",
        {"estimate": estimate},
        kind="confirm",
    )


def _plan_as_dict(plan: Plan) -> dict:
    return {"tool": plan.tool, "scope": plan.scope,
            "target_id": plan.target_id, "n_items": plan.n_items}


def _plan_from_dict(raw: dict) -> Plan:
    return Plan(kind="tool", tool=raw.get("tool", ""), scope=raw.get("scope", ""),
                target_id=raw.get("target_id"), n_items=int(raw.get("n_items") or 0))


# --- Gọi tool ---

def _run_summarize(doc: Document, plan: Plan) -> None:
    label = scope_lib.scope_label(doc, plan.scope, plan.target_id)
    payload = _call("summarize", doc, plan, label)
    if payload is None:
        return  # thất bại thì KHÔNG đá người dùng ra khỏi bài quiz đang làm dở
    state.set_last_scope(plan.scope, plan.target_id)
    # Yêu cầu này không phải quiz ⇒ trả cột trái về slide. Thiếu dòng này thì
    # bảng quiz của lượt trước nằm lại trên màn, và người vừa xin tóm tắt lại
    # thấy 4 đáp án trắc nghiệm không liên quan gì tới thứ họ hỏi.
    state.close_quiz()
    state.add_chat_turn("assistant", f"**Tóm tắt — {label}**", payload, kind="summary")


def _run_quiz(doc: Document, plan: Plan) -> None:
    label = scope_lib.scope_label(doc, plan.scope, plan.target_id)
    # Không truyền `variant` ⇒ `tools/quiz.py` tự lấy bộ đầu tiên chưa có trong
    # cache. Nhờ vậy xin quiz lần nữa trên cùng phạm vi luôn ra BỘ KHÁC, và bộ
    # mới còn biết bộ cũ đã hỏi ý gì để tránh — kể cả sau khi khởi động lại app.
    payload = _call("quiz", doc, plan, label)
    if payload is None:
        return
    state.set_last_scope(plan.scope, plan.target_id)

    items = payload.get("items") or []
    if not items:
        state.add_chat_turn(
            "assistant",
            f"Không câu nào trong {label} qua được bước kiểm trích dẫn, nên mình không "
            "hiển thị câu nào. Thử một phạm vi rộng hơn nhé.",
            payload, kind="error",
        )
        return

    state.open_quiz(payload)
    state.add_chat_turn(
        "assistant",
        f"Đã tạo **{len(items)} câu** từ {label}. Bảng làm bài đang mở bên trái — "
        "làm xong bấm *Nộp bài* để xem đúng/sai và giải thích.",
        payload, kind="quiz",
    )


def _run_ask(doc: Document, plan: Plan) -> None:
    state.set_pending(True)
    try:
        with st.spinner("Đang tìm trong tài liệu…"):
            payload = registry.run("ask", doc=doc, question=plan.question,
                                   scope=plan.scope or None, target_id=plan.target_id,
                                   history=_history_for_model(exclude_last=True))
    except AppError as exc:
        state.add_chat_turn("assistant", f"⚠ {exc.user_message}", kind="error")
        return
    finally:
        state.set_pending(False)

    # Câu trả lời nào cũng kèm nút "xem chỗ này" — phải có slide để bấm sang.
    state.close_quiz()
    state.add_chat_turn("assistant", _format_answer(payload), payload, kind="answer")


def _call(tool: str, doc: Document, plan: Plan, label: str) -> dict | None:
    """Gọi tool có tiến độ, và dịch mọi lỗi thành một lượt chat đọc được.

    Ba lớp chỗ khó đi qua đúng chỗ này: `NoGroundedSource` (lớp ①) thành một lời
    từ chối nói rõ lý do, `BudgetExceeded` thành cảnh báo, `AppError` còn lại
    thành một câu tiếng Việt — không lớp nào được biến thành traceback. Lớp ②
    không tới đây: `intent.py` đã hỏi lại trước khi tool chạy.
    """
    progress_bar = st.progress(0.0, text="Đang chuẩn bị…")

    def on_progress(done: int, total: int, step: str) -> None:
        progress_bar.progress(min(1.0, done / max(1, total)), text=f"{step} ({done}/{total})")

    kwargs: dict = {
        "doc": doc,
        "scope": plan.scope,
        "target_id": plan.target_id,
        "progress": on_progress,
    }
    if tool == "quiz":
        kwargs["n_items"] = plan.n_items

    state.set_pending(True)
    try:
        return registry.run(tool, **kwargs)
    except BudgetExceeded as exc:
        state.add_chat_turn("assistant", f"⚠ {exc.user_message}", kind="error")
    except AppError as exc:
        # Gồm NoGroundedSource (lớp ①): abstain và nói lý do, không tóm tắt bừa
        state.add_chat_turn("assistant", exc.user_message, kind="error")
    finally:
        state.set_pending(False)
        progress_bar.empty()
    return None


# --- "Tại sao câu 5 sai?" — trả lời từ bộ quiz đang mở, không gọi model ---

def _explain_quiz_item(plan: Plan) -> None:
    quiz = state.get_active_quiz() or {}
    items = quiz.get("items") or []
    item = items[plan.item_no - 1]  # intent.py đã kiểm khoảng hợp lệ

    lines = [
        f"**Câu {plan.item_no}.** {item.get('stem', '')}",
        f"\nĐáp án đúng: **{item.get('answer_text', '')}**",
    ]
    if item.get("explanation"):
        lines.append(f"\n{item['explanation']}")
    for reason in item.get("distractor_rationale") or []:
        lines.append(f"\n- {reason}")

    state.add_chat_turn("assistant", "\n".join(lines), {"item": item}, kind="explain")


# --- Vẽ hội thoại ---

def _render_history(doc: Document) -> None:
    history = state.chat_history()
    if not history:
        st.caption(
            f"Hỏi hoặc yêu cầu bất cứ gì về **{doc.source_name}** ({len(doc.pages)} trang). "
            "Mình tóm tắt, tạo quiz, hoặc trả lời câu hỏi — và luôn kèm trích dẫn trang."
        )
        return

    for index, turn in enumerate(history):
        with st.chat_message("user" if turn["role"] == "user" else "assistant"):
            st.markdown(turn["content"])
            _render_extras(turn, index)


def _render_extras(turn: dict, index: int) -> None:
    kind = turn.get("kind") or ""
    payload = turn.get("payload") or {}

    if kind == "summary":
        panel_summary.render(payload, index)
    elif kind == "answer":
        _render_citations(payload, index)
    elif kind == "quiz":
        _render_quiz_note(payload, index)
    elif kind == "explain":
        _render_item_source(payload.get("item") or {}, index)
    elif kind == "clarify":
        _render_options(payload.get("options") or [], index)
    elif kind == "confirm":
        _render_confirm(index)


def _render_options(options: list[str], index: int) -> None:
    """Lựa chọn cho câu hỏi làm rõ: bấm là gửi lại đúng câu đó, vẫn đi qua router."""
    if not options:
        return
    columns = st.columns(len(options))
    for column, option in zip(columns, options):
        with column:
            if st.button(option, key=f"opt-{index}-{option}", width="stretch"):
                _queue(option)


def _render_confirm(index: int) -> None:
    """Chạy trực tiếp Plan đã lưu, không route lại: câu hỏi cũ vẫn là câu hỏi cũ."""
    if state.get_pending_plan() is None:
        return
    run_col, skip_col = st.columns(2)
    with run_col:
        if st.button("Chạy", key=f"confirm-{index}", type="primary", width="stretch"):
            st.session_state["_chat_confirmed"] = True
            st.rerun()
    with skip_col:
        if st.button("Thôi", key=f"cancel-{index}", width="stretch"):
            state.set_pending_plan(None)
            st.rerun()


def _render_citations(payload: dict, turn_index: int) -> None:
    citations = payload.get("citations") or []
    meta = payload.get("_meta") or {}

    for cite_index, citation in enumerate(citations):
        page_no = int(citation.get("page_no") or 0)
        if not page_no:
            continue
        cite_col, quote_col = st.columns([1, 3])
        with cite_col:
            viewer.jump_button(f"↪ trang {page_no}", page_no,
                               key=f"chat-jump-{turn_index}-{cite_index}")
        with quote_col:
            st.caption(f"“{str(citation.get('quote', ''))[:160]}”")

    if meta.get("pages") and not citations:
        st.caption(f"Đã tìm ở trang: {', '.join(str(p) for p in meta['pages'])}")
    for warning in meta.get("warnings") or []:
        st.caption(f"⚠ {warning}")

    if meta.get("no_call"):
        st.caption("Không gọi AI cho câu này — không tìm thấy đoạn nào để trả lời.")
    elif meta.get("model"):
        st.caption(
            f"{'cache' if meta.get('cached') else 'sinh mới'} · {meta['model']} · "
            f"prompt {meta.get('prompt_version', '')}"
        )


def _is_on_screen(payload: dict) -> bool:
    """Bubble này có phải bộ quiz đang mở không.

    So theo `_meta` chứ không so bằng `is`: hai bộ khác nhau luôn khác ít nhất
    một trong ba trường dưới (variant tăng mỗi lần sinh), và cách so này không
    vỡ nếu payload bị sao chép ở đâu đó giữa đường.
    """
    active = (state.get_active_quiz() or {}).get("_meta") or {}
    if not active:
        return False
    meta = payload.get("_meta") or {}
    return all(active.get(field) == meta.get(field)
               for field in ("scope", "target_id", "variant"))


def _render_quiz_note(payload: dict, index: int) -> None:
    # Bộ này còn trên màn không? Nếu người dùng đã hỏi việc khác thì cột trái đã
    # về slide, và đây là đường duy nhất quay lại bài đang làm dở.
    if _is_on_screen(payload) and state.get_mode() != state.QUIZ:
        if st.button("↩ Mở lại bảng làm bài", key=f"reopen-{index}", width="stretch"):
            state.reopen_quiz()
            st.rerun()

    meta = payload.get("_meta") or {}
    if payload.get("notes"):
        st.info(payload["notes"])
    for warning in meta.get("warnings") or []:
        st.caption(f"⚠ {warning}")
    if len(meta.get("parts") or []) > 1:
        with st.expander(f"Bộ này ghép từ {len(meta['parts'])} phần"):
            for part in meta["parts"]:
                st.caption(f"{part['label']}: {part['items']}/{part.get('quota', '?')} câu")


def _render_item_source(item: dict, index: int) -> None:
    anchor = item.get("anchor") or {}
    page_no = int(anchor.get("page_no") or 0)
    if anchor.get("quote"):
        st.caption(f"nguồn: “{anchor['quote'][:160]}”")
    if page_no:
        viewer.jump_button(f"↪ trang {page_no}", page_no, key=f"explain-jump-{index}")


def _format_answer(payload: dict) -> str:
    answer = str(payload.get("answer", "") or "").strip()
    if payload.get("answerable"):
        return answer

    reason = _REFUSAL_HINT.get(str(payload.get("refusal_reason") or ""), "")
    parts = [answer or reason]
    if payload.get("followup"):
        parts.append(f"\n\n*{payload['followup']}*")
    return "".join(parts)


# --- Ngữ cảnh gửi cho router ---

def _ui_context(doc: Document) -> UIContext:
    quiz = state.get_active_quiz() or {}
    return UIContext(
        page_no=min(state.get_page_no(), len(doc.pages)),
        quiz_items=len(quiz.get("items") or []),
        last_scope=state.get_last_scope(),
    )


def _history_for_model(exclude_last: bool = False) -> list[dict]:
    """Lịch sử dạng phẳng cho model. Bỏ lượt cuối khi lượt đó CHÍNH LÀ câu đang xử lý."""
    turns = [{"role": t["role"], "content": t["content"]} for t in state.chat_history()]
    return turns[:-1] if exclude_last and turns else turns


def _run_confirmed_plan(doc: Document) -> None:
    """Người dùng bấm "Chạy" ở lượt trước ⇒ chạy thẳng Plan đã lưu, không route lại."""
    if not st.session_state.pop("_chat_confirmed", False):
        return
    raw = state.get_pending_plan()
    state.set_pending_plan(None)
    if raw:
        _run_scoped_tool(doc, _plan_from_dict(raw))
