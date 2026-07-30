"""Dò chương/mục theo thang 4 bậc, dừng ở bậc đầu tiên thành công.

TODO(CP4) cho bậc 1-3. Bảng 4 bậc: ARCHITECHTURE.md §5.
Không sửa Page/Block — chỉ nhóm chúng lại.

    1. toc        doc.get_toc() — bookmark có sẵn trong PDF
    2. heuristic  font lớn nhất + nửa trên trang => tiêu đề slide
    3. llm        một lời gọi trên DANH SÁCH TIÊU ĐỀ TRANG (không phải toàn văn)
    4. flat       không tách được — chỉ còn document + page

Bậc 4 KHÔNG phải lỗi: UI nói rõ lý do và disable tóm tắt theo chương/mục kèm
giải thích, thay vì hiện nút bấm vào ra rác (HAX G1).
"""

from __future__ import annotations

from pathlib import Path

from .models import Chapter, Page


def build_outline(pages: list[Page], pdf_path: Path | None = None) -> tuple[list[Chapter], str]:
    """Trả (chapters, outline_source).

    Hiện dừng ở bậc 4: trả danh sách RỖNG + 'flat'. Không dựng một chương giả
    tên "Document" — outline_source='flat' mà vẫn có chương là nói dối UI,
    và tóm tắt theo chương sẽ chạy trên một cấu trúc không có thật.
    """
    return [], "flat"


def from_toc(pdf_path: Path, pages: list[Page]) -> list[Chapter] | None:
    raise NotImplementedError("TODO(CP4)")


def from_heuristic(pages: list[Page]) -> list[Chapter] | None:
    raise NotImplementedError("TODO(CP4)")


def from_llm(pages: list[Page]) -> list[Chapter] | None:
    raise NotImplementedError("TODO(CP4): dùng prompts/outline.v1.md")
