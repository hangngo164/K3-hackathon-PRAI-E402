"""Lớp canh nguồn sự thật — kiểm bằng CODE, không bằng model.

Bảng kiểm đầy đủ: ARCHITECHTURE.md §11. Không gọi AI, không sửa nội dung.
Đã chạy: quote khớp nguồn + anchor hợp lệ. TODO(CP3): số liệu + luật quiz rác.

Chạy cho MỌI output trước khi tới UI. Fail thì loại và nói thật số lượng
thực tế ("chỉ tạo được 4/5 câu có căn cứ"), không im lặng hiển thị.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from .models import Anchor, ScopeContext


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reasons: list[str]


def normalize(text: str) -> str:
    """Gộp whitespace + lower — dùng cho cả hai phía khi so khớp."""
    return " ".join(text.lower().split())


def verify_quote_in_text(quote: str, text: str) -> bool:
    """Khớp tuyệt đối sau normalize (giữ tên cũ để tests/test_verify.py không vỡ)."""
    return normalize(quote) in normalize(text)


def quote_matches(quote: str, source: str, threshold: float = 0.92) -> bool:
    """Khớp tuyệt đối; không được thì fuzzy >= threshold (model hay sửa dấu câu)."""
    if verify_quote_in_text(quote, source):
        return True
    nq, ns = normalize(quote), normalize(source)
    if not nq or len(nq) > len(ns):
        return False
    window = len(nq)
    for start in range(0, len(ns) - window + 1, max(1, window // 4)):
        if difflib.SequenceMatcher(None, nq, ns[start:start + window]).ratio() >= threshold:
            return True
    return False


def verify_anchor(anchor: Anchor, scope_ids: list[str]) -> bool:
    """page_no và mọi block_id phải nằm trong unit_ids của scope (không rò trang ngoài)."""
    if f"p{anchor.page_no:02d}" not in scope_ids:
        return False
    return all(block_id in scope_ids for block_id in anchor.block_ids)


def check_anchor(anchor: Anchor, ctx: ScopeContext) -> CheckResult:
    """Quote tồn tại · page_no hợp lệ · block_ids thuộc scope."""
    reasons: list[str] = []
    if not verify_anchor(anchor, ctx.unit_ids):
        reasons.append(f"anchor trỏ ra ngoài scope: trang {anchor.page_no}, khối {anchor.block_ids}")
    if not quote_matches(anchor.quote, ctx.text):
        reasons.append(f"quote không có trong nguồn: {anchor.quote[:60]!r}")
    return CheckResult(passed=not reasons, reasons=reasons)


def check_numbers(text: str, source: str) -> CheckResult:
    """Mọi số trong output phải xuất hiện trong nguồn — fail thì cảnh báo, không tự loại."""
    raise NotImplementedError("TODO(CP3)")


def check_quiz_item(item: dict, ctx: ScopeContext) -> CheckResult:
    """Luật chống câu hỏi rác: 1 đáp án đúng · độ dài phương án chênh <=2.5x ·
    không hỏi hình thức tài liệu · stem không lộ đáp án.
    """
    raise NotImplementedError("TODO(CP3)")
