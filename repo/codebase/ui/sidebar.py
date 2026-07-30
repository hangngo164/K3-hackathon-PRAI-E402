import streamlit as st

from . import state


def show_sidebar(cache_dir):
    st.sidebar.title("Chọn tài liệu")
    uploaded = st.sidebar.file_uploader("Upload PDF hoặc PPTX", type=["pdf", "pptx"])
    if uploaded is not None:
        state.set_uploaded_file(uploaded)

    st.sidebar.markdown("---")
    st.sidebar.write("Cache path:")
    st.sidebar.code(str(cache_dir))

    st.sidebar.markdown("---")
    st.sidebar.write("Phiên hiện tại")
    st.sidebar.write(f"Trang: {state.get_page_no()}")
    st.sidebar.write(f"Scope: {state.get_uploaded_file().name if state.get_uploaded_file() else 'Chưa chọn tài liệu'}")
