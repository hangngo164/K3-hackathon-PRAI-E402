"""Cắt đúng lát văn bản — cửa DUY NHẤT mà summarize/quiz lấy được nội dung.

Bảng scope → nguồn → chiến lược: ARCHITECHTURE.md §8. Không gọi AI.
Đã chạy: selection + page. TODO(CP4): section/chapter/document + map-reduce.

Quyết định kiến trúc quan trọng nhất nằm ở đây: scope là CẤU TRÚC tài liệu
(người dùng đã chỉ đúng chỗ), không phải kết quả tìm kiếm. Nhờ vậy kiểm được
trích dẫn bằng code.
"""

from __future__ import annotations

from .config import settings
from .errors import NoGroundedSource, ScopeTooThin
from .models import Document, Scope, ScopeContext


def estimate_tokens(text: str) -> int:
    """Ước lượng thô cho tiếng Việt: ~3 ký tự/token. Chỉ dùng để chọn chiến lược."""
    return max(1, len(text) // 3)


def resolve(
    doc: Document,
    scope: Scope,
    target_id: str | None = None,
    selection_block_ids: list[str] | None = None,
) -> ScopeContext:
    """Trả văn bản của scope + chiến lược direct/map_reduce.

    KHÔNG BAO GIỜ tự cắt bớt văn bản: cắt bớt = tóm tắt thiếu mà người dùng không biết.
    Vượt MAX_DIRECT_TOKENS => strategy='map_reduce'.
    """
    cfg = settings()

    if scope == "selection":
        return _resolve_selection(doc, selection_block_ids or [], cfg)
    if scope == "page":
        return _resolve_page(doc, target_id, cfg)
    raise NotImplementedError(f"TODO(CP4): scope '{scope}' chưa hỗ trợ")


def _resolve_selection(doc: Document, block_ids: list[str], cfg) -> ScopeContext:
    """Text lấy từ CÁC KHỐI đã chọn + 1 khối liền kề mỗi phía làm ngữ cảnh (§8)."""
    if not block_ids:
        raise ScopeTooThin(user_message="Chưa chọn khối nào trên trang.")

    page = next((p for p in doc.pages if any(b.block_id in block_ids for b in p.blocks)), None)
    if page is None:
        raise ScopeTooThin(user_message="Không tìm thấy khối đã chọn trong tài liệu.")

    chosen = [b for b in page.blocks if b.block_id in block_ids]
    orders = [b.order for b in chosen]
    neighbours = [
        b for b in page.blocks
        if b.block_id not in block_ids and (b.order == min(orders) - 1 or b.order == max(orders) + 1)
    ]

    text = "\n".join(b.text for b in chosen)
    if len(text.split()) < cfg.min_words_per_selection:
        raise ScopeTooThin(
            user_message=(
                f"Đoạn bạn chọn chỉ có {len(text.split())} từ. "
                f"Mở rộng ra cả trang, hay vẫn làm trên đoạn ngắn này?"
            )
        )

    unit_ids = [f"p{page.page_no:02d}"] + [b.block_id for b in chosen]
    return ScopeContext(
        scope="selection",
        target_id=None,
        unit_ids=unit_ids,
        text=text,
        est_tokens=estimate_tokens(text),
        strategy="direct",
        context_text="\n".join(b.text for b in neighbours),
    )


def _resolve_page(doc: Document, target_id: str | None, cfg) -> ScopeContext:
    page_no = int(target_id) if target_id is not None else 1
    page = doc.page(page_no)
    if page is None:
        raise ScopeTooThin(user_message=f"Không có trang {page_no} trong tài liệu.")

    if page.char_count < cfg.min_chars_per_page:
        raise NoGroundedSource(
            user_message=(
                f"Trang {page_no} chủ yếu là hình — mình không đọc được nội dung trong ảnh, "
                f"nên không tóm tắt để tránh nói sai."
            )
        )

    unit_ids = [f"p{page.page_no:02d}"] + [b.block_id for b in page.blocks]
    est = estimate_tokens(page.text)
    return ScopeContext(
        scope="page",
        target_id=str(page_no),
        unit_ids=unit_ids,
        text=page.text,
        est_tokens=est,
        strategy="direct" if est <= cfg.max_direct_tokens else "map_reduce",
    )


def plan_map_reduce(doc: Document, scope: Scope, target_id: str | None) -> list[str]:
    """Danh sách unit_id cần tóm tắt ở tầng dưới trước khi reduce.

    Tái dùng cache: tóm tắt trang -> mục -> chương -> tài liệu.
    Vượt MAX_JOB_CALLS => ném BudgetExceeded để UI hỏi trước.
    """
    raise NotImplementedError("TODO(CP4)")
