"""Data structures shared by the PDF pipeline and the Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    """A selectable text block extracted from one PDF page."""

    block_id: str
    page_no: int
    order: int
    text: str
    bbox: tuple[float, float, float, float]
    font_size_max: float


@dataclass(frozen=True)
class Page:
    """Parsed content and the rendered image for one 1-based page."""

    page_no: int
    blocks: tuple[Block, ...]
    text: str
    image_png: bytes
    width_pt: float
    height_pt: float


@dataclass(frozen=True)
class Document:
    """An uploaded PDF prepared for the CP2 viewer."""

    doc_hash: str
    source_name: str
    pages: tuple[Page, ...]

