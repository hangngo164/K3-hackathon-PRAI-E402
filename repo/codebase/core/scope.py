"""Cắt đúng lát văn bản — cửa DUY NHẤT mà summarize/quiz lấy được nội dung.

TODO(CP3) cho selection + page · TODO(CP4) cho section/chapter/document + map-reduce.
Bảng scope → nguồn → chiến lược: ARCHITECHTURE.md §8.
Không gọi AI.

Quyết định kiến trúc quan trọng nhất nằm ở đây: scope là CẤU TRÚC tài liệu
(người dùng đã chỉ đúng chỗ), không phải kết quả tìm kiếm. Nhờ vậy kiểm được
trích dẫn bằng code.
"""

from __future__ import annotations

from .models import Anchor, Document, Scope, ScopeContext


def estimate_tokens(text: str) -> int:
    """Ước lượng thô cho tiếng Việt: ~3 ký tự/token. Chỉ dùng để chọn chiến lược."""
    raise NotImplementedError("TODO(CP3)")


def resolve(
    doc: Document,
    scope: Scope,
    target_id: str | None = None,
    selection: Anchor | None = None,
) -> ScopeContext:
    """Trả văn bản của scope + chiến lược direct/map_reduce.

    selection: thêm 1 khối liền kề mỗi phía làm ngữ cảnh, đánh dấu rõ là ngữ cảnh
               (không được tóm tắt vào). Quá ngắn => ném ScopeTooThin (lớp ②).
    page:      char_count dưới ngưỡng => ném NoGroundedSource (lớp ①).
    Vượt MAX_DIRECT_TOKENS => strategy='map_reduce'. KHÔNG BAO GIỜ tự cắt bớt
    văn bản: cắt bớt = tóm tắt thiếu mà người dùng không biết.
    """
    raise NotImplementedError("TODO(CP3)")


def plan_map_reduce(doc: Document, scope: Scope, target_id: str | None) -> list[str]:
    """Danh sách unit_id cần tóm tắt ở tầng dưới trước khi reduce.

    Tái dùng cache: tóm tắt trang -> mục -> chương -> tài liệu.
    Vượt MAX_JOB_CALLS => ném BudgetExceeded để UI hỏi trước.
    """
    raise NotImplementedError("TODO(CP4)")
