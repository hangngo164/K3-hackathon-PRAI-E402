"""Render helpers for the CP2 block-picker highlight."""

from __future__ import annotations

import io
from collections.abc import Iterable

from PIL import Image, ImageDraw

from core.models import Block


def pdf_to_px(bbox: tuple[float, float, float, float], dpi: int) -> tuple[int, int, int, int]:
    """Convert a PyMuPDF point-based bounding box to rendered-image pixels."""

    scale = dpi / 72
    return tuple(round(value * scale) for value in bbox)  # type: ignore[return-value]


def render_highlights(
    page_png: bytes,
    blocks: Iterable[Block],
    selected_block_ids: set[str],
    dpi: int,
) -> bytes:
    """Draw translucent yellow overlays over the selected source blocks."""

    image = Image.open(io.BytesIO(page_png)).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for block in blocks:
        if block.block_id not in selected_block_ids:
            continue
        x0, y0, x1, y1 = pdf_to_px(block.bbox, dpi)
        draw.rectangle((x0, y0, x1, y1), fill=(255, 210, 0, 92), outline=(213, 142, 0, 240), width=3)

    rendered = Image.alpha_composite(image, overlay).convert("RGB")
    output = io.BytesIO()
    rendered.save(output, format="PNG")
    return output.getvalue()
