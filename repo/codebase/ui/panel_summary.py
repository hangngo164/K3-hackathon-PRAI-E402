import streamlit as st

from core.models import Document
from . import state


def show_tab(doc: Document) -> None:
    scope = state.get_selected_blocks() and "selection" or "page"
    st.write(f"Scope hiện tại: {scope}")
    st.write("Tính năng tóm tắt chưa được triển khai đầy đủ.")
    st.info("Chọn khối và bấm quiz để kiểm tra luồng. Tạm thời chưa có output tóm tắt.")
