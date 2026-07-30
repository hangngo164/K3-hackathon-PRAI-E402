"""Sinh câu hỏi ôn tập có neo nguồn, cân cơ cấu độ khó, chạy vòng repair.

TODO(CP3) selection · TODO(CP4) theo mục/chương/tài liệu.
Vòng sinh→kiểm→sửa + luật chống câu hỏi rác: ARCHITECHTURE.md §10.
Không tự kiểm trích dẫn (việc của verify.py).

Mức tự động hoá: AUGMENT — đáp án sai dạy học viên kiến thức sai trước kỳ
đánh giá, sửa đắt. Luôn hiện trích dẫn để người dùng tự kiểm trước khi tin.
"""

from __future__ import annotations

from .models import Document, Scope


def generate(
    doc: Document,
    scope: Scope,
    target_id: str | None = None,
    selection_block_ids: list[str] | None = None,
    n_items: int = 5,
) -> dict:
    """Trả payload theo QUIZ_SCHEMA, đã qua verify.

    Sinh dư 2 item để sau khi loại vẫn đủ n_items — rẻ hơn một vòng sinh lại.
    Nguồn mỏng => tạo tối đa số câu chống đỡ được và NÓI RÕ, không nhồi câu trùng.
    """
    raise NotImplementedError("TODO(CP3)")


def repair(item: dict, reasons: list[str], ctx_text: str) -> dict | None:
    """Sửa một item fail, tối đa 1 lượt. Vẫn fail => trả None (loại item).

    Dùng lại prompts/quiz.v1.md với biến {{repair_feedback}} — không cần prompt riêng.
    """
    raise NotImplementedError("TODO(CP3)")


def allocate_quota(doc: Document, scope: Scope, target_id: str | None, n_items: int) -> dict[str, int]:
    """Chia hạn ngạch câu hỏi theo trang/mục/chương TRƯỚC khi sinh.

    Để model tự chọn thì câu hỏi dồn hết vào phần đầu tài liệu.
    """
    raise NotImplementedError("TODO(CP4)")
