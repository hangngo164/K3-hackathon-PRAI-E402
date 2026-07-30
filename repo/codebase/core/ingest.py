"""File slide → Document (trang, khối văn bản, bbox).

Pipeline 6 bước: ARCHITECHTURE.md §6.
Không render ảnh ngoài pipeline này, không dò chương/mục (outline.py).

    bytes -> hash -> cache hit? -> (pptx? convert) -> fitz parse -> lọc block rác -> outline -> lưu
"""

from __future__ import annotations

from pathlib import Path

import fitz

from . import cache, convert, outline
from .config import settings
from .errors import ConvertError, IngestError
from .models import Block, Document, Page


def ingest(data: bytes, source_name: str) -> Document:
    """Cửa vào duy nhất. Cache hit thì nạp lại từ .cache/, không parse lần hai.

    doc_hash luôn tính trên BYTES GỐC người dùng nạp (kể cả .pptx) để khoá cache
    và Document.doc_hash không bao giờ lệch nhau.
    """
    doc_hash = cache.file_hash(data)
    cached = cache.load_document(doc_hash)
    if cached is not None:
        return cached

    out_dir = cache.doc_dir(doc_hash)
    suffix = Path(source_name).suffix.lower()
    source_kind = "pptx" if suffix == ".pptx" else "pdf"
    source_path = out_dir / f"source{suffix or '.pdf'}"
    source_path.write_bytes(data)

    if source_kind == "pptx":
        pdf_path = convert.pptx_to_pdf(source_path, out_dir)
        if pdf_path is None:
            raise ConvertError(
                user_message="Máy này chưa có LibreOffice nên chưa đổi được PPTX sang PDF. "
                             "Hãy xuất slide ra PDF rồi nạp lại."
            )
    else:
        pdf_path = source_path

    document = parse_pdf(pdf_path, out_dir, source_name, doc_hash, source_kind)
    cache.save_document(document)
    return document


def parse_pdf(pdf_path: Path, out_dir: Path, source_name: str,
              doc_hash: str, source_kind: str) -> Document:
    dpi = settings().page_dpi
    try:
        pdf = fitz.open(pdf_path)
    except Exception as exc:  # file hỏng, sai định dạng, có mật khẩu
        raise IngestError(user_message=f"Không đọc được file: {exc}") from exc

    pages: list[Page] = []
    for idx, page in enumerate(pdf, start=1):
        text = page.get_text("text")
        blocks: list[Block] = []
        for block_index, block_data in enumerate(page.get_text("dict").get("blocks", []), start=1):
            if not block_data.get("lines"):
                continue
            block_text = "\n".join(
                " ".join(span.get("text", "") for span in line.get("spans", []))
                for line in block_data.get("lines", [])
            ).strip()
            if not block_text:
                continue
            font_size_max = max(
                (span.get("size", 0)
                 for line in block_data.get("lines", [])
                 for span in line.get("spans", [])),
                default=0.0,
            )
            blocks.append(Block(
                block_id=f"p{idx:02d}-b{block_index:02d}",
                page_no=idx,
                order=block_index,
                text=block_text,
                bbox=tuple(block_data["bbox"]),
                font_size_max=font_size_max,
                is_title_like=False,
            ))

        png_path = out_dir / "png" / f"p{idx:02d}.png"
        png_path.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(dpi=dpi).save(png_path)

        pages.append(Page(
            page_no=idx,
            blocks=blocks,
            text=text,
            png_path=str(png_path),
            char_count=len(text.strip()),
        ))
    pdf.close()

    pages = drop_boilerplate(pages)
    chapters, outline_source = outline.build_outline(pages, pdf_path)
    return Document(
        doc_hash=doc_hash,
        source_name=source_name,
        source_kind=source_kind,
        pages=pages,
        chapters=chapters,
        outline_source=outline_source,
    )


def drop_boilerplate(pages: list[Page]) -> list[Page]:
    """Bỏ header/footer lặp lại >60% số trang và block chỉ chứa số trang.

    TODO(CP2): chưa lọc, hiện trả nguyên. Bước 4 của pipeline §6.
    """
    return pages


def page_blocks(doc: Document, page_no: int) -> list[Block]:
    """Danh sách khối cho block picker của viewer."""
    page = doc.page(page_no)
    return page.blocks if page else []
