"""Lớp canh nguồn sự thật — kiểm bằng CODE, không bằng model.

TODO(CP3). Bảng kiểm đầy đủ: ARCHITECHTURE.md §11.
Không gọi AI, không sửa nội dung — chỉ trả pass/fail + lý do.

Chạy cho MỌI output trước khi tới UI. Fail thì loại và nói thật số lượng
thực tế ("chỉ tạo được 4/5 câu có căn cứ"), không im lặng hiển thị.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Anchor, ScopeContext


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reasons: list[str]


def normalize(text: str) -> str:
    """Gộp whitespace, bỏ dấu câu dư, lower — dùng cho cả hai phía khi so khớp."""
    raise NotImplementedError("TODO(CP3)")


def quote_matches(quote: str, source: str, threshold: float = 0.92) -> bool:
    """Khớp tuyệt đối sau normalize; không được thì fuzzy (difflib) >= threshold."""
    raise NotImplementedError("TODO(CP3)")


def check_anchor(anchor: Anchor, ctx: ScopeContext) -> CheckResult:
    """Quote tồn tại · page_no hợp lệ · block_ids thuộc scope (không rò trang ngoài)."""
    raise NotImplementedError("TODO(CP3)")


def check_numbers(text: str, source: str) -> CheckResult:
    """Mọi số trong output phải xuất hiện trong nguồn — fail thì cảnh báo, không tự loại."""
    raise NotImplementedError("TODO(CP3)")


def check_quiz_item(item: dict, ctx: ScopeContext) -> CheckResult:
    """Luật chống câu hỏi rác: 1 đáp án đúng · độ dài phương án chênh <=2.5x ·
    không hỏi hình thức tài liệu · stem không lộ đáp án.
    """
    raise NotImplementedError("TODO(CP3)")
