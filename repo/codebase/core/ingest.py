"""File slide → Document (trang, khối văn bản, bbox).

TODO(CP2). Pipeline 6 bước: ARCHITECHTURE.md §6.
Không render ảnh (render.py), không dò chương/mục (outline.py).

    bytes -> hash -> cache hit? -> (pptx? convert) -> fitz parse -> lọc block rác -> outline -> lưu
"""

from __future__ import annotations

from pathlib import Path

from .models import Block, Document, Page


def ingest(data: bytes, source_name: str) -> Document:
    """Cửa vào duy nhất. Cache hit thì nạp lại từ .cache/, không parse lần hai."""
    raise NotImplementedError("TODO(CP2)")


def parse_pdf(pdf_path: Path) -> list[Page]:
    """page.get_text('dict') -> Block (text, bbox, font_size_max)."""
    raise NotImplementedError("TODO(CP2)")


def drop_boilerplate(pages: list[Page]) -> list[Page]:
    """Bỏ header/footer lặp lại >60% số trang và block chỉ chứa số trang."""
    raise NotImplementedError("TODO(CP2)")


def page_blocks(doc: Document, page_no: int) -> list[Block]:
    """Danh sách khối cho block picker của viewer."""
    raise NotImplementedError("TODO(CP2)")
