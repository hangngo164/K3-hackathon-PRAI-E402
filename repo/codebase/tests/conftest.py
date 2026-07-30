"""Fixture dùng chung: một Document bịa, không cần PDF thật, không gọi AI.

Dựng tay thay vì đọc file mẫu để test chạy nhanh và không phụ thuộc PyMuPDF —
mọi thứ được kiểm ở đây (scope, outline, verify, retrieve, hạn ngạch quiz) đều
là logic thuần trên `Document`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("TRACE_DISABLE", "1")  # test không ghi vào eval/traces/

from agent_core.models import Block, Chapter, Document, Page, Section  # noqa: E402

# Độ dài cố ý gần với slide thật: đủ vượt MIN_CHARS_PER_PAGE (120) và
# MIN_WORDS_PER_SELECTION (40), nếu không thì mọi test scope đều đâm vào nhánh
# abstain và không kiểm được thứ định kiểm.
_PAGE_TEXT = {
    1: [("Kiến trúc Transformer", 20.0),
        ("Buổi 3 — tổng quan mô hình encoder-decoder, cơ chế attention, "
         "và cách mã hoá vị trí cho chuỗi đầu vào.", 11.0),
        ("Nội dung: self-attention, multi-head attention, positional encoding, "
         "và phần bài tập cuối buổi.", 11.0)],
    2: [("Self-Attention", 20.0),
        ("Attention tính trọng số giữa các token trong cùng một chuỗi, cho phép mỗi "
         "vị trí nhìn sang mọi vị trí khác mà không cần đi tuần tự như mạng hồi quy.", 11.0),
        ("Công thức dùng ba ma trận Query, Key và Value, được tạo ra từ cùng một vector "
         "đầu vào bằng ba phép chiếu tuyến tính khác nhau.", 11.0)],
    3: [("Self-Attention", 20.0),
        ("Query là vector biểu diễn token đang xét, dùng để hỏi xem những token còn lại "
         "trong chuỗi có liên quan tới nó tới mức nào.", 11.0),
        ("Key dùng để so khớp với Query, còn Value mang thông tin thực sự được lấy ra "
         "sau khi đã tính xong trọng số attention.", 11.0)],
    4: [("Positional Encoding", 20.0),
        ("Transformer xử lý cả chuỗi cùng lúc nên không có thông tin thứ tự sẵn, "
         "phải cộng thêm một vector vị trí vào embedding đầu vào.", 11.0),
        ("Bản gốc dùng hàm sin và cos với 512 chiều, mỗi chiều một tần số khác nhau "
         "để mô hình suy ra được khoảng cách tương đối giữa hai token.", 11.0)],
}


def _make_page(page_no: int, entries: list[tuple[str, float]]) -> Page:
    blocks = [
        Block(
            block_id=f"p{page_no:02d}-b{order:02d}",
            page_no=page_no,
            order=order,
            text=text,
            bbox=(50.0, 40.0 + order * 60, 500.0, 90.0 + order * 60),
            font_size_max=size,
            is_title_like=size >= 18.0,
        )
        for order, (text, size) in enumerate(entries, start=1)
    ]
    joined = "\n".join(b.text for b in blocks)
    return Page(page_no=page_no, blocks=blocks, text=joined,
                png_path=f"/tmp/p{page_no:02d}.png", char_count=len(joined.strip()))


@pytest.fixture
def pages() -> list[Page]:
    return [_make_page(no, entries) for no, entries in sorted(_PAGE_TEXT.items())]


@pytest.fixture
def image_only_page() -> Page:
    """Trang toàn hình: layer text gần trống => phải abstain, không được tóm tắt bừa."""
    return Page(page_no=5, blocks=[], text="", png_path="/tmp/p05.png", char_count=0)


@pytest.fixture
def doc(pages, image_only_page) -> Document:
    chapters = [
        Chapter(unit_id="ch01", title="Self-Attention", page_range=(1, 3), sections=[
            Section(unit_id="ch01-s01", title="Tổng quan", page_range=(1, 1), chapter_id="ch01"),
            Section(unit_id="ch01-s02", title="Query/Key/Value", page_range=(2, 3),
                    chapter_id="ch01"),
        ]),
        Chapter(unit_id="ch02", title="Positional Encoding", page_range=(4, 5), sections=[]),
    ]
    return Document(
        doc_hash="testhash00000000",
        source_name="slide-demo.pdf",
        source_kind="pdf",
        pages=pages + [image_only_page],
        chapters=chapters,
        outline_source="heuristic",
    )
