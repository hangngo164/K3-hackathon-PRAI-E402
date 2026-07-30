import streamlit as st

from core import llm
from . import state


def show_chat(doc=None) -> None:
    st.header("Chat")
    history = state.get_chat_history()
    for msg in history:
        if msg["role"] == "user":
            st.markdown(f"**You:** {msg['text']}")
        else:
            st.markdown(f"**Assistant:** {msg['text']}")

    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Gửi tin nhắn")
        submitted = st.form_submit_button("Gửi")
        if submitted and user_input:
            state.append_chat_message("user", user_input)
            with st.spinner("Đang gọi LLM…"):
                reply = llm.simple_chat(user_input)
            state.append_chat_message("assistant", reply)
            st.rerun()

    if st.button("Xóa lịch sử chat"):
        state.clear_chat()
        st.rerun()
