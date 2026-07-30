import streamlit as st

from core.models import Document
from . import state


def show_tab(doc: Document) -> None:
    selected_blocks = state.get_selected_blocks()
    if not selected_blocks:
        st.warning("Hãy chọn ít nhất một block rồi mới tạo quiz.")
        return
    st.write("Tạo quiz từ vùng đã chọn")
    if st.button("Sinh quiz"):
        st.write("Quiz generator chưa hoàn thiện. Hiện mới hiển thị luồng demo.")
    st.info("Chọn khối rồi bấm Sinh quiz. Sau đó UI sẽ hiển thị các câu hỏi có trích dẫn.")
