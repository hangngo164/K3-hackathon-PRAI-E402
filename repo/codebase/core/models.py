"""Kiểu dữ liệu dùng chung + serde JSON cho cache.

TODO(CP2). Thiết kế đầy đủ: ARCHITECHTURE.md §5.
Không parse PDF, không gọi AI — chỉ là hình dạng của dữ liệu.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Scope = Literal["document", "chapter", "section", "page", "selection"]
BBox = tuple[float, float, float, float]  # đơn vị point (72dpi) như PyMuPDF trả về


@dataclass(frozen=True)
class Block:
    """Một khối văn bản trên trang — đơn vị nhỏ nhất người dùng bôi đen được."""

    block_id: str  # "p06-b03"
    page_no: int  # 1-based
    order: int
    text: str
    bbox: BBox
    font_size_max: float = 0.0
    is_title_like: bool = False


@dataclass(frozen=True)
class Page:
    page_no: int
    blocks: list[Block]
    text: str
    png_path: str = ""

    @property
    def char_count(self) -> int:
        """Dưới config.min_chars_per_page => trang thiên về hình => abstain (lớp ①)."""
        return len(self.text.strip())


@dataclass(frozen=True)
class Section:
    unit_id: str  # "ch02-s03"
    title: str
    page_range: tuple[int, int]
    chapter_id: str


@dataclass(frozen=True)
class Chapter:
    unit_id: str  # "ch02"
    title: str
    page_range: tuple[int, int]
    sections: list[Section]


@dataclass(frozen=True)
class Anchor:
    """Neo nguồn — mọi bullet tóm tắt và mọi câu quiz đều phải có."""

    page_no: int
    block_ids: list[str]
    quote: str  # <=200 ký tự, phải khớp văn bản gốc (verify.py kiểm)


@dataclass(frozen=True)
class Document:
    doc_hash: str  # sha256 bytes file gốc — khoá cache
    source_name: str
    source_kind: Literal["pdf", "pptx"]
    pages: list[Page]
    chapters: list[Chapter]
    outline_source: Literal["toc", "heuristic", "llm", "flat"]


@dataclass(frozen=True)
class ScopeContext:
    """Kết quả của scope.resolve() — thứ duy nhất summarize/quiz được nhận."""

    scope: Scope
    target_id: str | None
    unit_ids: list[str]
    text: str
    est_tokens: int
    strategy: Literal["direct", "map_reduce"]


# --- serde cho cache (.cache/<doc_hash>/doc.json) ---


def document_to_dict(doc: Document) -> dict:
    raise NotImplementedError("TODO(CP2): dataclasses.asdict + bbox tuple -> list")


def document_from_dict(raw: dict) -> Document:
    raise NotImplementedError("TODO(CP2): dựng lại Document, bbox list -> tuple")
