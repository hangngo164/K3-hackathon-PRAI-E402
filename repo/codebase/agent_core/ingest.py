"""File slide → Document (trang, khối văn bản, bbox).

    bytes -> hash -> cache hit? -> (pptx? convert) -> fitz parse -> lọc block rác -> outline -> lưu

Không render ảnh ngoài pipeline này, không tự dò chương/mục (việc của outline.py).

Một quyết định đáng chú ý: `Page.text` được DỰNG LẠI từ các khối còn sống sau
bước lọc, không lấy nguyên `get_text("text")`. Lý do: `verify.py` đối chiếu quote
vào `Page.text` còn anchor lại trỏ vào `block_id`. Hai nguồn lệch nhau thì có
quote hợp lệ vẫn bị loại oan (hoặc ngược lại), và đó là loại lỗi rất khó nhìn ra.
"""

from __future__ import annotations

from pathlib import Path
from statistics import median

import fitz

from . import cache, convert, outline
from .config import settings
from .errors import ConvertError, IngestError
from .log import trace
from .models import Block, Document, Page
from .outline import Grouper

_TITLE_TOP_RATIO = 0.45
_TITLE_FONT_RATIO = 1.15
_BOILERPLATE_PAGE_RATIO = 0.6   # lặp y hệt trên hơn 60% số trang => header/footer
_BOILERPLATE_MAX_CHARS = 200    # chân trang nhiều dòng ("Tên tác giả / Khoá luận / Hà Nội,
                                # tháng 6 2025") dài hơn 80 ký tự — để ngưỡng thấp thì
                                # đúng loại rác hay gặp nhất lại lọt qua
_MIN_PAGES_FOR_BOILERPLATE = 4


def ingest(data: bytes, source_name: str, outline_grouper: Grouper | None = None) -> Document:
    """Cửa vào duy nhất. Cache hit thì nạp lại từ `.cache/`, không parse lần hai.

    `doc_hash` luôn tính trên BYTES GỐC người dùng nạp (kể cả .pptx) để khoá
    cache và `Document.doc_hash` không bao giờ lệch nhau.

    `outline_grouper` là bậc 3 của thang dò chương/mục. Truyền None thì thang
    dừng ở bậc heuristic — nạp file vẫn chạy được khi chưa có API key.
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

    document = parse_pdf(pdf_path, out_dir, source_name, doc_hash, source_kind, outline_grouper)
    cache.save_document(document)
    trace(
        "ingest",
        doc_hash=doc_hash,
        source_name=source_name,
        source_kind=source_kind,
        pages=len(document.pages),
        chapters=len(document.chapters),
        outline_source=document.outline_source,
    )
    return document


def parse_pdf(pdf_path: Path, out_dir: Path, source_name: str, doc_hash: str,
              source_kind: str, outline_grouper: Grouper | None = None) -> Document:
    dpi = settings().page_dpi
    try:
        pdf = fitz.open(pdf_path)
    except Exception as exc:  # file hỏng, sai định dạng, có mật khẩu
        raise IngestError(user_message=f"Không đọc được file: {exc}") from exc

    if getattr(pdf, "needs_pass", False):
        pdf.close()
        raise IngestError(
            user_message="File PDF này có mật khẩu. Hãy bỏ mật khẩu rồi nạp lại."
        )
    if pdf.page_count == 0:
        pdf.close()
        raise IngestError(user_message="File PDF không có trang nào.")

    try:
        toc = pdf.get_toc()
    except Exception:
        toc = []

    pages: list[Page] = []
    for idx, page in enumerate(pdf, start=1):
        blocks = _parse_blocks(page, idx)

        png_path = out_dir / "png" / f"p{idx:02d}.png"
        png_path.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(dpi=dpi).save(png_path)

        pages.append(_make_page(idx, blocks, str(png_path)))
    pdf.close()

    pages = drop_boilerplate(pages)
    chapters, outline_source = outline.build_outline(pages, toc=toc, grouper=outline_grouper)
    return Document(
        doc_hash=doc_hash,
        source_name=source_name,
        source_kind=source_kind,
        pages=pages,
        chapters=chapters,
        outline_source=outline_source,
    )


def _parse_blocks(page, page_no: int) -> list[Block]:
    """Khối văn bản + bbox + cỡ chữ. `is_title_like` tính so với thân bài CỦA TRANG ĐÓ.

    So theo từng trang chứ không theo cả tài liệu: slide tiêu đề và slide nội
    dung có thang cỡ chữ khác nhau, lấy chuẩn chung thì trang nào chữ to cũng
    thành "toàn tiêu đề".
    """
    raw: list[dict] = []
    for order, data in enumerate(page.get_text("dict").get("blocks", []), start=1):
        lines = data.get("lines")
        if not lines:
            continue  # block ảnh — không có text, bỏ qua ở đây (trang toàn ảnh => abstain sau)
        # Gộp khoảng trắng trong từng dòng: PDF căn đều hay mã hoá giãn chữ bằng
        # nhiều space liền nhau, và chuỗi đó đi thẳng vào prompt, vào trích dẫn
        # hiển thị cho người dùng, rồi vào cả câu hỏi quiz. Giữ xuống dòng vì
        # ranh giới dòng là thông tin thật của slide.
        text = "\n".join(
            " ".join(
                " ".join(span.get("text", "") for span in line.get("spans", [])).split()
            )
            for line in lines
        ).strip()
        if not text:
            continue
        raw.append({
            "order": order,
            "text": text,
            "bbox": tuple(data["bbox"]),
            "font": max(
                (span.get("size", 0) for line in lines for span in line.get("spans", [])),
                default=0.0,
            ),
        })

    if not raw:
        return []

    body_font = median([b["font"] for b in raw if b["font"] > 0] or [12.0])
    page_height = float(getattr(page.rect, "height", 0) or max(b["bbox"][3] for b in raw))

    return [
        Block(
            block_id=f"p{page_no:02d}-b{item['order']:02d}",
            page_no=page_no,
            order=item["order"],
            text=item["text"],
            bbox=item["bbox"],
            font_size_max=item["font"],
            is_title_like=(
                item["font"] >= body_font * _TITLE_FONT_RATIO
                and item["bbox"][1] <= page_height * _TITLE_TOP_RATIO
            ),
        )
        for item in raw
    ]


def _make_page(page_no: int, blocks: list[Block], png_path: str) -> Page:
    """`text` dựng từ chính các khối — xem ghi chú đầu file."""
    text = "\n".join(b.text for b in blocks)
    return Page(
        page_no=page_no,
        blocks=blocks,
        text=text,
        png_path=png_path,
        char_count=len(text.strip()),
    )


def drop_boilerplate(pages: list[Page]) -> list[Page]:
    """Bỏ header/footer lặp lại trên >60% số trang, và khối chỉ chứa số trang.

    Vì sao đáng làm: một dòng chân trang "AI Thực Chiến — 2026" lặp trên 40
    trang sẽ chiếm chỗ trong mọi scope, ăn token của mọi lời gọi, và tệ nhất là
    làm mồi cho câu quiz rác kiểu "khoá học tên gì".

    Chỉ lọc khối NGẮN: một đoạn dài lặp lại nhiều trang là nội dung thật (định
    nghĩa được nhắc lại), không phải chrome của slide.
    """
    if len(pages) < _MIN_PAGES_FOR_BOILERPLATE:
        return pages

    counts: dict[str, int] = {}
    for page in pages:
        for key in {_boilerplate_key(b) for b in page.blocks if _is_short(b)}:
            counts[key] = counts.get(key, 0) + 1

    threshold = len(pages) * _BOILERPLATE_PAGE_RATIO
    repeated = {key for key, count in counts.items() if count > threshold}

    cleaned: list[Page] = []
    for page in pages:
        kept = [
            b for b in page.blocks
            if not (_is_short(b) and _boilerplate_key(b) in repeated)
            and not _is_page_number(b)
        ]
        # Không bao giờ xoá sạch một trang: thà giữ chrome còn hơn biến trang có
        # chữ thành trang "toàn hình" rồi abstain nhầm.
        cleaned.append(_make_page(page.page_no, kept or page.blocks, page.png_path))
    return cleaned


def _is_short(block: Block) -> bool:
    return len(block.text.strip()) <= _BOILERPLATE_MAX_CHARS


def _boilerplate_key(block: Block) -> str:
    """Chuẩn hoá + bỏ chữ số: 'Trang 3/40' và 'Trang 7/40' phải coi là một."""
    normalized = " ".join(block.text.lower().split())
    return "".join(ch for ch in normalized if not ch.isdigit())


def _is_page_number(block: Block) -> bool:
    stripped = block.text.strip()
    return bool(stripped) and all(ch.isdigit() or ch in "/-. " for ch in stripped)


def page_blocks(doc: Document, page_no: int) -> list[Block]:
    """Danh sách khối cho block picker của viewer."""
    page = doc.page(page_no)
    return page.blocks if page else []
