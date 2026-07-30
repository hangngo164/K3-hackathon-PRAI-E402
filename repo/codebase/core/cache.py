import json
from pathlib import Path

from .models import Document


def ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)


def doc_cache_path(cache_dir: Path, doc_hash: str) -> Path:
    return cache_dir / doc_hash


def save_document(cache_dir: Path, document: Document) -> None:
    doc_path = doc_cache_path(cache_dir, document.doc_hash) / "doc.json"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    with doc_path.open("w", encoding="utf-8") as f:
        json.dump({
            "doc_hash": document.doc_hash,
            "source_name": document.source_name,
            "source_kind": document.source_kind,
            "outline_source": document.outline_source,
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
                            "bbox": b.bbox,
                            "font_size_max": b.font_size_max,
                            "is_title_like": b.is_title_like,
                        }
                        for b in p.blocks
                    ],
                }
                for p in document.pages
            ],
            "chapters": [],
        }, f, ensure_ascii=False, indent=2)


def load_document(cache_dir: Path, doc_hash: str) -> Document | None:
    doc_path = doc_cache_path(cache_dir, doc_hash) / "doc.json"
    if not doc_path.exists():
        return None
    with doc_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    pages = []
    for page in data["pages"]:
        from .models import Block, Page

        blocks = [Block(**block) for block in page["blocks"]]
        pages.append(Page(
            page_no=page["page_no"],
            blocks=blocks,
            text=page["text"],
            png_path=page["png_path"],
            char_count=page["char_count"],
        ))
    return Document(
        doc_hash=data["doc_hash"],
        source_name=data["source_name"],
        source_kind=data["source_kind"],
        pages=pages,
        chapters=[],
        outline_source=data.get("outline_source", "flat"),
    )
