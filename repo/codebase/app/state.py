"""Khai báo khoá `session_state` + get/set có kiểm tra.

Streamlit chạy lại TOÀN BỘ script sau mỗi tương tác. Mọi thứ đắt (parse, render,
gọi AI) phải nằm trong cache trên đĩa hoặc `session_state`. Cache đĩa là nguồn
sự thật; `session_state` chỉ là bản sao cho phiên hiện tại.

Điểm khác so với bản một-file: trang đang xem, lịch sử chat, bộ quiz đang mở và
chế độ giao diện đều lưu THEO TỪNG `doc_hash`. Nhờ vậy đổi qua lại giữa các file
slide không mất chỗ đang đọc — đúng thứ người dùng cần khi ôn nhiều buổi cùng lúc.
"""

from __future__ import annotations

import streamlit as st

DEFAULTS: dict = {
    "docs": {},            # doc_hash -> {"name", "size", "kind"}
    "active_doc": None,    # doc_hash đang đọc
    "page_no": {},         # doc_hash -> int
    "chat": {},            # doc_hash -> list[{"role", "content", "kind", "payload"}]
    "last_scope": {},      # doc_hash -> (scope, target_id) — phạm vi lượt trước, cho "phần đó"
    "results": {},         # doc_hash -> {"summarize|page|6": payload}
    "mode": {},            # doc_hash -> "normal" | "quiz"
    "active_quiz": {},     # doc_hash -> payload bộ quiz đang mở trong Quiz Mode
    "quiz_run": 0,         # số thứ tự bộ quiz trong phiên — vào key widget, xem open_quiz()
    "pending_plan": {},    # doc_hash -> Plan đang chờ người dùng xác nhận (job lớn)
    "quiz_answers": {},    # doc_hash -> {item_id: option_index}
    "quiz_graded": {},     # doc_hash -> bool
    "pending": False,      # job đang chạy => khoá nút, tránh double-submit khi rerun
    "use_llm_outline": True,
}

NORMAL, QUIZ = "normal", "quiz"


def initialize_session_state() -> None:
    """Gọi một lần ở đầu `app/main.py`."""
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value.copy() if isinstance(value, dict) else value


# --- Danh sách tài liệu ---

def register_doc(doc_hash: str, name: str, size: int, kind: str) -> None:
    """Ghi nhận một file đã nạp. Nạp lại cùng file thì không tạo bản ghi thứ hai."""
    st.session_state.docs[doc_hash] = {"name": name, "size": size, "kind": kind}
    if st.session_state.active_doc is None:
        st.session_state.active_doc = doc_hash


def docs() -> dict[str, dict]:
    return st.session_state.docs


def forget_docs(keep: set[str]) -> None:
    """Bỏ tài liệu người dùng đã gỡ khỏi ô upload, kèm mọi trạng thái của nó."""
    buckets = ("docs", "page_no", "chat", "last_scope", "results", "mode",
               "active_quiz", "pending_plan", "quiz_answers", "quiz_graded")
    for doc_hash in [h for h in st.session_state.docs if h not in keep]:
        for bucket in buckets:
            st.session_state[bucket].pop(doc_hash, None)
    if st.session_state.active_doc not in st.session_state.docs:
        st.session_state.active_doc = next(iter(st.session_state.docs), None)


def active_doc_hash() -> str | None:
    return st.session_state.active_doc


def set_active_doc(doc_hash: str) -> None:
    st.session_state.active_doc = doc_hash


# --- Trạng thái theo từng tài liệu ---

def _current() -> str:
    return st.session_state.active_doc or "-"


def get_page_no() -> int:
    return st.session_state.page_no.get(_current(), 1)


def set_page_no(page_no: int) -> None:
    st.session_state.page_no[_current()] = max(1, page_no)


def get_last_scope() -> tuple[str, str | None] | None:
    """Phạm vi của lượt CHẠY TRƯỚC — thứ duy nhất giải được "tạo quiz từ phần đó".

    Khác trang đang xem: người dùng có thể tóm tắt chương 2 rồi lật sang trang 30
    để xem, và "phần đó" vẫn phải trỏ về chương 2.
    """
    return st.session_state.last_scope.get(_current())


def set_last_scope(scope: str, target_id: str | None = None) -> None:
    st.session_state.last_scope[_current()] = (scope, target_id)


# --- Chế độ giao diện: Normal (slide + chat) / Quiz (bảng làm bài + chat) ---

def get_mode() -> str:
    return st.session_state.mode.get(_current(), NORMAL)


def set_mode(mode: str) -> None:
    st.session_state.mode[_current()] = mode


def get_active_quiz() -> dict | None:
    """Bộ quiz đang mở trong Quiz Mode. `results` giữ mọi bộ đã sinh; đây chỉ trỏ tới bộ trên màn."""
    return st.session_state.active_quiz.get(_current())


def open_quiz(payload: dict) -> None:
    """Mở một bộ quiz mới và cấp cho nó một số thứ tự riêng trong phiên.

    `quiz_run` đi vào KEY của mọi widget trong `panel_quiz`. Cần thiết vì
    `_renumber()` luôn đánh lại item thành q1..qN, nên bộ mới dùng lại đúng key
    `quiz-q1` của bộ cũ — mà Streamlit giữ giá trị widget theo key, và giá trị
    đã lưu THẮNG tham số `index`. Không có số này thì bộ quiz mới hiện sẵn đáp
    án người dùng đã chọn ở bộ trước, dù `reset_quiz()` đã xoá `quiz_answers`.
    """
    st.session_state.quiz_run += 1
    st.session_state.active_quiz[_current()] = payload
    reset_quiz()
    set_mode(QUIZ)


def quiz_run() -> int:
    return st.session_state.quiz_run



def close_quiz() -> None:
    """Đóng bảng làm bài, GIỮ đáp án đã chọn và giữ nguyên lịch sử chat."""
    set_mode(NORMAL)


def reopen_quiz() -> None:
    """Mở lại bộ quiz đang có mà KHÔNG xoá đáp án — khác `open_quiz()` ở đúng chỗ đó.

    Cần vì tóm tắt/hỏi đáp giờ tự đưa cột trái về slide: không có đường quay lại
    thì một câu hỏi giữa chừng làm mất bài đang làm dở.
    """
    if get_active_quiz():
        set_mode(QUIZ)


# --- Job lớn chờ xác nhận ---

def get_pending_plan() -> dict | None:
    return st.session_state.pending_plan.get(_current())


def set_pending_plan(plan: dict | None) -> None:
    if plan is None:
        st.session_state.pending_plan.pop(_current(), None)
    else:
        st.session_state.pending_plan[_current()] = plan


# --- Chat ---

def chat_history() -> list[dict]:
    return st.session_state.chat.setdefault(_current(), [])


def add_chat_turn(role: str, content: str, payload: dict | None = None,
                  kind: str = "") -> None:
    """`kind` quyết định bubble được vẽ bằng renderer nào: summary · quiz · answer · clarify · explain."""
    chat_history().append({"role": role, "content": content, "kind": kind, "payload": payload})


def clear_chat() -> None:
    st.session_state.chat[_current()] = []


# --- Khoá nút khi có job đang chạy ---

def is_pending() -> bool:
    return bool(st.session_state.pending)


def set_pending(value: bool) -> None:
    st.session_state.pending = value


# --- Kết quả đã sinh, giữ qua các lần rerun ---

def _result_key(kind: str, scope: str, target_id: str | None, extra: str = "") -> str:
    return f"{kind}|{scope}|{target_id or '-'}|{extra}"


def get_result(kind: str, scope: str, target_id: str | None, extra: str = "") -> dict | None:
    """Giữ payload trong phiên để rerun (bấm "xem chỗ này", lật trang) không gọi lại tool.

    Cache trên đĩa cũng chặn được lời gọi AI, nhưng vẫn tốn một vòng đọc file
    và một lượt verify cho mỗi lần Streamlit vẽ lại — mà nó vẽ lại rất nhiều.
    """
    bucket = st.session_state.results.get(_current(), {})
    return bucket.get(_result_key(kind, scope, target_id, extra))


def set_result(kind: str, scope: str, target_id: str | None, payload: dict,
               extra: str = "") -> None:
    bucket = st.session_state.results.setdefault(_current(), {})
    bucket[_result_key(kind, scope, target_id, extra)] = payload


def clear_results(kind: str | None = None) -> None:
    bucket = st.session_state.results.get(_current(), {})
    for key in [k for k in bucket if kind is None or k.startswith(f"{kind}|")]:
        bucket.pop(key, None)


# --- Trạng thái làm bài quiz ---

def quiz_answers() -> dict[str, int]:
    return st.session_state.quiz_answers.setdefault(_current(), {})


def set_quiz_answer(item_id: str, option_index: int) -> None:
    quiz_answers()[item_id] = option_index


def is_quiz_graded() -> bool:
    return bool(st.session_state.quiz_graded.get(_current()))


def set_quiz_graded(value: bool) -> None:
    st.session_state.quiz_graded[_current()] = value


def reset_quiz() -> None:
    st.session_state.quiz_answers[_current()] = {}
    st.session_state.quiz_graded[_current()] = False


def goto(page_no: int) -> None:
    """Nhảy tới nguồn — dùng bởi nút "xem chỗ này" trên bullet, câu quiz, trích dẫn chat.

    Nhảy nguồn luôn ĐƯA VỀ Normal Mode: đang làm quiz mà bấm "xem chỗ này" thì
    thứ người dùng muốn là cái slide, và Quiz Mode đang che nó. Đáp án đã chọn
    vẫn giữ (`quiz_answers` không bị xoá) nên quay lại làm tiếp được.
    """
    set_page_no(page_no)
    set_mode(NORMAL)
