import streamlit as st


def initialize_session_state() -> None:
    defaults = {
        "doc_hash": None,
        "page_no": 1,
        "selected_block_ids": [],
        "scope": "page",
        "target_id": None,
        "results": {},
        "pending": False,
        "cost": {"calls": 0, "tokens": 0},
        "uploaded_file": None,
        "chat_history": [],
        "chat_context": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_uploaded_file(uploaded_file) -> None:
    st.session_state.uploaded_file = uploaded_file


def get_uploaded_file():
    return st.session_state.uploaded_file


def get_chat_history() -> list:
    return st.session_state.chat_history


def append_chat_message(role: str, text: str) -> None:
    st.session_state.chat_history.append({"role": role, "text": text})


def clear_chat() -> None:
    st.session_state.chat_history = []


def set_page_no(page_no: int) -> None:
    st.session_state.page_no = page_no


def get_page_no() -> int:
    return st.session_state.page_no


def set_selected_blocks(block_ids: list[str]) -> None:
    st.session_state.selected_block_ids = block_ids


def get_selected_blocks() -> list[str]:
    return st.session_state.selected_block_ids


def set_result(key: tuple, value) -> None:
    st.session_state.results[key] = value


def get_result(key: tuple):
    return st.session_state.results.get(key)
