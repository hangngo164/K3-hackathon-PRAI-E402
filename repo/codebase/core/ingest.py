import hashlib
from pathlib import Path

import fitz

from .cache import save_document
from .convert import pptx_to_pdf
from .models import Block, Document, Page
from .outline import build_outline


def compute_doc_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def parse_pdf(pdf_path: Path, cache_dir: Path, source_name: str) -> Document:
    doc = fitz.open(pdf_path)
    pages = []
    for idx, page in enumerate(doc, start=1):
        blocks = []
        text = page.get_text("text")
        char_count = len(text)
        blocks_data = page.get_text("dict").get("blocks", [])
        for block_index, block_data in enumerate(blocks_data, start=1):
            if not block_data.get("lines"):
                continue
            block_text = "\n".join(
                " ".join(span.get("text", "") for span in line.get("spans", []))
                for line in block_data.get("lines", [])
            ).strip()
            if not block_text:
                continue
            bbox = tuple(block_data["bbox"])
            font_size_max = max((span.get("size", 0) for line in block_data.get("lines", []) for span in line.get("spans", [])), default=0)
            blocks.append(Block(
                block_id=f"p{idx:02d}-b{block_index:02d}",
                page_no=idx,
                order=block_index,
                text=block_text,
                bbox=bbox,
                font_size_max=font_size_max,
                is_title_like=False,
            ))
        png_path = cache_dir / f"png/p{idx:02d}.png"
        pix = page.get_pixmap(dpi=110)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(png_path)
        pages.append(Page(
            page_no=idx,
            blocks=blocks,
            text=text,
            png_path=str(png_path),
            char_count=char_count,
        ))
    chapters, outline_source = build_outline(pages)
    document = Document(
        doc_hash=compute_doc_hash(pdf_path.read_bytes()),
        source_name=source_name,
        source_kind="pdf",
        pages=pages,
        chapters=chapters,
        outline_source=outline_source,
    )
    save_document(cache_dir, document)
    return document


def load_document(uploaded_file, cache_dir: Path) -> Document | None:
    file_bytes = uploaded_file.read()
    doc_hash = compute_doc_hash(file_bytes)
    doc_cache_dir = cache_dir / doc_hash
    existing = None
    if (doc_cache_dir / "doc.json").exists():
        from .cache import load_document as load_doc

        existing = load_doc(cache_dir, doc_hash)
    if existing is not None:
        return existing
    source_path = cache_dir / f"input_{doc_hash}{Path(uploaded_file.name).suffix}"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_bytes(file_bytes)
    if source_path.suffix.lower() == ".pptx":
        pdf_path = pptx_to_pdf(source_path, doc_cache_dir)
        if pdf_path is None:
            return None
    else:
        pdf_path = source_path
    return parse_pdf(pdf_path, doc_cache_dir, uploaded_file.name)
