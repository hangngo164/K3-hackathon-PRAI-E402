"""Entrypoint Streamlit — chỉ layout + điều phối, không chứa logic nghiệp vụ.

Chạy:  streamlit run app/main.py

Bố cục `st.columns([3, 2])`: phải LUÔN là cửa sổ chat — chỗ duy nhất người dùng
ra yêu cầu. Cột trái đổi theo đúng hai trạng thái:

    Normal Mode   slide viewer
    Quiz Mode     bảng làm bài

Đổi trạng thái là đổi `state.get_mode()`, không mở route mới, không reload trang,
không popup — nên lịch sử chat và trang đang xem đi qua chuyển trạng thái mà
không mất gì.

Hai cột cuộn RIÊNG: mỗi cột nằm trong một `st.container(height=...)` chiều cao cố
định, nên cuộn lịch sử chat không kéo slide ra khỏi màn hình và ngược lại. Đây là
lý do phải dùng chiều cao pixel thay vì `height="stretch"`: stretch chỉ bám theo
container cha, mà cột top-level không bị chặn chiều cao nên nó không chặn được gì.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# Streamlit chạy file này như một script nên sys.path[0] là thư mục app/.
# Thêm codebase/ vào đường import TRƯỚC mọi import nội bộ, nếu không thì
# `import agent_core` không thấy gì.
CODEBASE_DIR = Path(__file__).resolve().parents[1]
if str(CODEBASE_DIR) not in sys.path:
    sys.path.insert(0, str(CODEBASE_DIR))

st.set_page_config(page_title="Trợ lý Ôn Slide", layout="wide")

# Chiều cao hai vùng cuộn. Chọn 660 để vừa một trình duyệt cao ~900px mà cả hai
# cột còn nằm trọn trong màn — đây là điều kiện để "vừa xem slide vừa chat".
PANE_HEIGHT = 660
CHAT_INPUT_HEIGHT = 200  # ô nhập + hai nút, phần bị trừ ra khỏi vùng cuộn lịch sử

# Streamlit chừa sẵn ~6rem padding trên. Trừ bớt để hai vùng cuộn cao 660px không
# đẩy chính trang web thành có thanh cuộn — mà đó đúng là thứ cần tránh ở đây.
st.markdown(
    "<style>.block-container{padding-top:2.5rem;padding-bottom:1rem;}</style>",
    unsafe_allow_html=True,
)

# Đẩy st.secrets vào os.environ TRƯỚC khi import agent_core: agent_core không
# được import streamlit, nên nó chỉ đọc được biến môi trường.
try:
    for _key in ("OPENAI_API_KEY", "OPENAI_MODEL_FAST", "OPENAI_MODEL_MAIN", "LLM_PROVIDER"):
        if _key in st.secrets:
            os.environ.setdefault(_key, str(st.secrets[_key]))
except Exception:
    pass  # không có .streamlit/secrets.toml thì dùng .env — không phải lỗi

from agent_core import ingest  # noqa: E402
from agent_core.config import reset_settings_cache, settings  # noqa: E402
from agent_core.errors import AppError  # noqa: E402
from app import chat, panel_quiz, sidebar, state, viewer  # noqa: E402

reset_settings_cache()
state.initialize_session_state()


@st.cache_data(show_spinner=False, max_entries=8)
def load_document(data: bytes, source_name: str, use_llm_outline: bool):
    """Cache theo NỘI DUNG file: Streamlit rerun mỗi tương tác, không parse lại.

    `use_llm_outline` nằm trong khoá cache vì nó đổi kết quả (có/không có cây
    chương mục), không phải một tuỳ chọn hiển thị.
    """
    grouper = None
    if use_llm_outline and settings().has_api_key:
        from tools.outline import group_pages
        grouper = group_pages
    return ingest.ingest(data, source_name, outline_grouper=grouper)


uploaded_files = sidebar.show_upload()

documents: dict[str, object] = {}
for uploaded in uploaded_files:
    try:
        with st.spinner(f"Đang xử lý {uploaded.name}…"):
            # getvalue() chứ không read(): read() ở rerun sau trả b"" vì con trỏ ở EOF
            data = uploaded.getvalue()
            doc = load_document(data, uploaded.name, st.session_state.use_llm_outline)
    except AppError as exc:
        st.sidebar.error(f"{uploaded.name}: {exc.user_message}")
        continue

    documents[doc.doc_hash] = doc
    state.register_doc(doc.doc_hash, doc.source_name, len(data), doc.source_kind)

state.forget_docs(set(documents))
sidebar.show_status(documents)

st.title("Trợ lý Ôn Slide")

active = state.active_doc_hash()
if active is None or active not in documents:
    st.info(
        "Nạp một hoặc nhiều file slide (PDF, hoặc PPTX nếu máy có LibreOffice) để bắt đầu. "
        "Nạp nhiều file thì chọn file muốn đọc ở thanh bên trái."
    )
    st.stop()

doc = documents[active]

col_main, col_chat = st.columns([3, 2])

# ĐỪNG ĐẢO THỨ TỰ HAI KHỐI DƯỚI ĐÂY.
#
# `chat.show_chat()` là chỗ DUY NHẤT đổi được UI mode (sinh quiz xong thì gọi
# `state.open_quiz()`), còn cột trái chỉ ĐỌC mode. Streamlit chạy script một
# lượt từ trên xuống, nên cột nào đọc trước sẽ đọc phải giá trị cũ: vẽ viewer
# xong rồi mode mới đổi sang QUIZ, và bảng làm bài phải đợi tới lượt chạy sau
# mới hiện — đúng lỗi "phải gõ thêm một tin nhắn nữa quiz mới ra".
#
# `st.columns` giữ chỗ theo VỊ TRÍ chứ không theo thứ tự thực thi, nên ghi vào
# `col_chat` trước vẫn hiển thị bên phải. Cách này chốt state trước rồi mới vẽ,
# thay vì rải `st.rerun()` vào từng đường vào — mỗi rerun tốn trọn một lượt
# chạy lại, và đường vào thứ tư thêm sau này sẽ lại quên.
with col_chat:
    # Ô nhập nằm NGOÀI vùng cuộn: kéo lại lịch sử cũ mà mất chỗ gõ là hỏng đúng
    # thứ người dùng đang định làm.
    chat.show_chat(doc, history_height=PANE_HEIGHT - CHAT_INPUT_HEIGHT)

with col_main:
    with st.container(height=PANE_HEIGHT, border=False):
        if state.get_mode() == state.QUIZ:
            panel_quiz.show_quiz(doc)
        else:
            viewer.show_viewer(doc)
