"""Trang → PNG, đổi toạ độ pdf→px, vẽ overlay highlight.

Thiết kế: ARCHITECHTURE.md §7. Không đọc text (việc của ingest.py).

CẢNH BÁO: bbox của PyMuPDF theo point (72dpi), ảnh render ở PAGE_DPI.
Hệ số scale = dpi/72 nằm DUY NHẤT trong pdf_to_px() — sai chỗ này là lỗi
"highlight lệch chỗ", có test riêng: tests/test_bbox_scale.py.
`dpi` bắt buộc truyền vào: không đặt mặc định để tránh hai nguồn sự thật với
PAGE_DPI trong .env.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .models import BBox

HIGHLIGHT_RGBA = (255, 214, 0, 90)  # vàng, alpha ~0.35


def pdf_to_px(bbox: BBox, dpi: int) -> tuple[int, int, int, int]:
    """Đổi bbox point (72dpi) sang pixel của ảnh render ở `dpi`."""
    scale = dpi / 72.0
    return tuple(int(coord * scale) for coord in bbox)


def draw_highlight(image_path: Path | str, boxes: list[tuple[int, int, int, int]],
                   output_path: Path | str) -> Path:
    """Vẽ hình chữ nhật vàng trong suốt lên ảnh trang (PIL RGBA composite)."""
    image = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    for box in boxes:
        draw.rectangle(box, fill=HIGHLIGHT_RGBA)
    Image.alpha_composite(image, overlay).convert("RGB").save(output_path)
    return Path(output_path)
