"""Bước 0 — trang kiểm tra môi trường.

TẠM THỜI: file này chỉ để xác nhận Streamlit + PyMuPDF + Pillow + OpenAI chạy được
trên máy. Ở CP2 nó được thay bằng layout thật (viewer + panel) theo ARCHITECHTURE.md §16.

Chạy:  streamlit run app.py
"""

from __future__ import annotations

import io
import os
import shutil
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent

st.set_page_config(page_title="Trợ lý Ôn Slide — kiểm tra môi trường", layout="wide")

# st.secrets -> os.environ, để core/ không phải import streamlit (ARCHITECHTURE.md §3)
for _k in ("OPENAI_API_KEY", "OPENAI_MODEL_FAST", "OPENAI_MODEL_MAIN"):
    try:
        if _k in st.secrets and not os.getenv(_k):
            os.environ[_k] = str(st.secrets[_k])
    except Exception:  # noqa: BLE001 — không có secrets.toml là chuyện bình thường
        pass

try:
    from dotenv import load_dotenv

    load_dotenv(HERE / ".env")
except ImportError:
    pass

st.title("Bước 0 — môi trường")
st.caption("Trang tạm để kiểm tra toolchain. CP2 sẽ thay bằng viewer + panel thật.")

left, right = st.columns([2, 3])

with left:
    st.subheader("Kiểm tra")
    rows = []
    for name, label in [("streamlit", "streamlit"), ("openai", "openai"),
                        ("fitz", "pymupdf"), ("pptx", "python-pptx"), ("PIL", "pillow")]:
        try:
            mod = __import__(name)
            ver = getattr(mod, "__version__", None) or getattr(mod, "version", "?")
            rows.append({"thành phần": label, "trạng thái": "ok", "chi tiết": str(ver)})
        except ImportError:
            rows.append({"thành phần": label, "trạng thái": "THIẾU", "chi tiết": "pip install -r requirements.txt"})

    key = os.getenv("OPENAI_API_KEY", "").strip()
    rows.append({
        "thành phần": "OPENAI_API_KEY",
        "trạng thái": "ok" if key and not key.startswith("sk-thay-bang") else "THIẾU",
        "chi tiết": f"...{key[-4:]}" if key else "điền vào .env",
    })
    rows.append({"thành phần": "model FAST", "trạng thái": "ok",
                 "chi tiết": os.getenv("OPENAI_MODEL_FAST", "(chưa đặt)")})
    rows.append({"thành phần": "model MAIN", "trạng thái": "ok",
                 "chi tiết": os.getenv("OPENAI_MODEL_MAIN", "(chưa đặt)")})
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    rows.append({"thành phần": "LibreOffice", "trạng thái": "ok" if soffice else "thiếu (không chặn)",
                 "chi tiết": soffice or "PPTX sẽ dùng fallback python-pptx"})
    st.dataframe(rows, hide_index=True, use_container_width=True)

with right:
    st.subheader("Thử render một PDF")
    up = st.file_uploader("Chọn file PDF bất kỳ để xác nhận PyMuPDF render được", type=["pdf"])
    if up is not None:
        import fitz

        doc = fitz.open(stream=up.getvalue(), filetype="pdf")
        dpi = int(os.getenv("PAGE_DPI", "110"))
        page_no = st.number_input("Trang", 1, doc.page_count, 1, key="smoke_page")
        page = doc[int(page_no) - 1]
        png = page.get_pixmap(dpi=dpi).tobytes("png")
        st.image(io.BytesIO(png), caption=f"{up.name} — trang {page_no}/{doc.page_count} @ {dpi}dpi",
                 use_container_width=True)
        blocks = [b for b in page.get_text("blocks") if b[4].strip()]
        st.caption(f"PyMuPDF đọc được {len(blocks)} khối văn bản trên trang này "
                   f"({len(page.get_text().strip())} ký tự) — nền cho tính năng bôi đen F3.3.")
        doc.close()
