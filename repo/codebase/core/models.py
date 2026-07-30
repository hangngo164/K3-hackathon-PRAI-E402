from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Block:
    block_id: str
    page_no: int
    order: int
    text: str
    bbox: tuple[float, float, float, float]
    font_size_max: float
    is_title_like: bool

@dataclass(frozen=True)
class Page:
    page_no: int
    blocks: list[Block]
    text: str
    png_path: str
    char_count: int

@dataclass(frozen=True)
class Section:
    unit_id: str
    title: str
    page_range: tuple[int, int]
    chapter_id: str

@dataclass(frozen=True)
class Chapter:
    unit_id: str
    title: str
    page_range: tuple[int, int]
    sections: list[Section]

@dataclass(frozen=True)
class Document:
    doc_hash: str
    source_name: str
    source_kind: Literal["pdf", "pptx"]
    pages: list[Page]
    chapters: list[Chapter]
    outline_source: Literal["toc", "heuristic", "llm", "flat"]

@dataclass(frozen=True)
class Anchor:
    page_no: int
    block_ids: list[str]
    quote: str

Scope = Literal["document", "chapter", "section", "page", "selection"]

@dataclass(frozen=True)
class ScopeContext:
    scope: Scope
    unit_ids: list[str]
    text: str
    est_tokens: int
    strategy: str
    anchors_available: list[Anchor]
