"""Small, explicit session-state helpers for the CP2 prototype."""

from __future__ import annotations

import streamlit as st


def init_state() -> None:
    st.session_state.setdefault("active_doc_hash", None)
    st.session_state.setdefault("page_no", 1)
    st.session_state.setdefault("mock_summary", None)
    st.session_state.setdefault("mock_quiz", None)
    st.session_state.setdefault("quiz_scored", False)


def open_document(doc_hash: str) -> None:
    """Reset per-document interactions when a new upload is opened."""

    if st.session_state.active_doc_hash == doc_hash:
        return

    st.session_state.active_doc_hash = doc_hash
    st.session_state.page_no = 1
    st.session_state.mock_summary = None
    st.session_state.mock_quiz = None
    st.session_state.quiz_scored = False
    clear_selection(doc_hash)


def clear_selection(doc_hash: str) -> None:
    prefix = f"selected:{doc_hash}:"
    for key in list(st.session_state):
        if key.startswith(prefix):
            del st.session_state[key]


def selected_ids(doc_hash: str, page_no: int) -> set[str]:
    prefix = f"selected:{doc_hash}:{page_no}:"
    return {key.removeprefix(prefix) for key, value in st.session_state.items() if key.startswith(prefix) and value}

