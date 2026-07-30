"""Kiểu dữ liệu dùng chung + serde JSON cho cache.

Thiết kế: ARCHITECHTURE.md §5. Không parse PDF, không gọi AI.
Serde nằm ở đây (không ở cache.py) theo STRUCTURE.md §3: cache.py chỉ đọc/ghi,
không được biết nội dung nghĩa là gì.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

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
    font_size_max: float
    is_title_like: bool


@dataclass(frozen=True)
class Page:
    page_no: int
    blocks: list[Block]
    text: str
    png_path: str
    char_count: int  # dưới settings.min_chars_per_page => trang thiên về hình => abstain (lớp ①)


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

    def page(self, page_no: int) -> Page | None:
        return next((p for p in self.pages if p.page_no == page_no), None)


@dataclass(frozen=True)
class ScopeContext:
    """Kết quả của scope.resolve() — thứ duy nhất summarize/quiz được nhận."""

    scope: Scope
    target_id: str | None
    unit_ids: list[str]  # gồm cả id trang VÀ id khối trong phạm vi (verify.py đối chiếu vào đây)
    text: str
    est_tokens: int
    strategy: Literal["direct", "map_reduce"]
    context_text: str = ""  # ngữ cảnh lân cận — chỉ để model hiểu, KHÔNG tóm tắt vào
    anchors_available: list[Anchor] | None = None


# --- serde cho cache (.cache/<doc_hash>/doc.json) ---


def document_to_dict(doc: Document) -> dict[str, Any]:
    return {
        "doc_hash": doc.doc_hash,
        "source_name": doc.source_name,
        "source_kind": doc.source_kind,
        "outline_source": doc.outline_source,
        "pages": [
            {
                "page_no": p.page_no,
                "text": p.text,
                "png_path": str(p.png_path),
                "char_count": p.char_count,
                "blocks": [
                    {
                        "block_id": b.block_id,
                        "page_no": b.page_no,
                        "order": b.order,
                        "text": b.text,
                        "bbox": list(b.bbox),
                        "font_size_max": b.font_size_max,
                        "is_title_like": b.is_title_like,
                    }
                    for b in p.blocks
                ],
            }
            for p in doc.pages
        ],
        "chapters": [
            {
                "unit_id": c.unit_id,
                "title": c.title,
                "page_range": list(c.page_range),
                "sections": [
                    {
                        "unit_id": s.unit_id,
                        "title": s.title,
                        "page_range": list(s.page_range),
                        "chapter_id": s.chapter_id,
                    }
                    for s in c.sections
                ],
            }
            for c in doc.chapters
        ],
    }


def document_from_dict(raw: dict[str, Any]) -> Document:
    pages = [
        Page(
            page_no=p["page_no"],
            blocks=[
                Block(
                    block_id=b["block_id"],
                    page_no=b["page_no"],
                    order=b["order"],
                    text=b["text"],
                    bbox=tuple(b["bbox"]),
                    font_size_max=b["font_size_max"],
                    is_title_like=b["is_title_like"],
                )
                for b in p["blocks"]
            ],
            text=p["text"],
            png_path=p["png_path"],
            char_count=p["char_count"],
        )
        for p in raw["pages"]
    ]
    chapters = [
        Chapter(
            unit_id=c["unit_id"],
            title=c["title"],
            page_range=tuple(c["page_range"]),
            sections=[
                Section(
                    unit_id=s["unit_id"],
                    title=s["title"],
                    page_range=tuple(s["page_range"]),
                    chapter_id=s["chapter_id"],
                )
                for s in c.get("sections", [])
            ],
        )
        for c in raw.get("chapters", [])
    ]
    return Document(
        doc_hash=raw["doc_hash"],
        source_name=raw["source_name"],
        source_kind=raw["source_kind"],
        pages=pages,
        chapters=chapters,
        outline_source=raw.get("outline_source", "flat"),
    )
