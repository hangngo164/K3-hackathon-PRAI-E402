import streamlit as st
from PIL import Image

from core.models import Document
from . import state
from core.render import draw_highlight, pdf_to_px


def show_viewer(doc: Document) -> None:
    page_no = state.get_page_no()
    page = next((p for p in doc.pages if p.page_no == page_no), None)
    if page is None:
        st.warning("Trang không tìm thấy")
        return
    st.subheader(f"Trang {page_no}")
    image = Image.open(page.png_path)
    selected_blocks = state.get_selected_blocks()

    if selected_blocks:
        boxes = []
        for block in page.blocks:
            if block.block_id in selected_blocks:
                boxes.append(pdf_to_px(block.bbox))
        highlighted_path = page.png_path.replace(".png", "_highlighted.png")
        draw_highlight(page.png_path, boxes, highlighted_path)
        st.image(Image.open(highlighted_path), use_column_width=True)
    else:
        st.image(image, use_column_width=True)

    st.write("Chọn khối văn bản để xét scope:")
    block_ids = [block.block_id for block in page.blocks]
    chosen = st.multiselect("Khối (block)", block_ids, default=selected_blocks)
    if chosen != selected_blocks:
        state.set_selected_blocks(chosen)

    if st.button("Chuyển sang trang trước"):
        if page_no > 1:
            state.set_page_no(page_no - 1)
            st.experimental_rerun()
    if st.button("Chuyển sang trang sau"):
        if page_no < len(doc.pages):
            state.set_page_no(page_no + 1)
            st.experimental_rerun()
