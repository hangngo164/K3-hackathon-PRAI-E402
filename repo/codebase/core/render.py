"""Trang → PNG, đổi toạ độ pdf→px, vẽ overlay highlight.

TODO(CP2). Thiết kế: ARCHITECHTURE.md §7.
Không đọc text (việc của ingest.py).

CẢNH BÁO: bbox của PyMuPDF theo point (72dpi), ảnh render ở PAGE_DPI.
Hệ số scale = dpi/72 phải nằm DUY NHẤT trong pdf_to_px() — sai chỗ này là lỗi
"highlight lệch chỗ", có test riêng: tests/test_bbox_scale.py.
"""

from __future__ import annotations

from pathlib import Path

from .models import BBox

HIGHLIGHT_RGB = (255, 214, 0)
HIGHLIGHT_ALPHA = 0.35


def pdf_to_px(bbox: BBox, dpi: int) -> tuple[int, int, int, int]:
    """Đổi bbox point (72dpi) sang pixel của ảnh render ở `dpi`."""
    raise NotImplementedError("TODO(CP2): scale = dpi / 72")


def render_pages(pdf_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    """Render TẤT CẢ trang một lượt lúc ingest — điều hướng sau đó tức thời."""
    raise NotImplementedError("TODO(CP2): page.get_pixmap(dpi=dpi)")


def draw_highlight(png_path: Path, bboxes: list[BBox], dpi: int, out_path: Path) -> Path:
    """Vẽ hình chữ nhật vàng trong suốt lên ảnh trang (PIL RGBA composite)."""
    raise NotImplementedError("TODO(CP2)")
