"""Cắt đúng lát văn bản — cửa DUY NHẤT mà `tools/` lấy được nội dung tài liệu.

Không gọi AI. Không tóm tắt. Chỉ trả lời: "phạm vi này gồm chữ nào, neo được
vào đâu, và nên gọi model theo chiến lược nào".

Quyết định kiến trúc quan trọng nhất nằm ở đây: với tóm tắt và quiz, scope là
CẤU TRÚC tài liệu — quy về một danh sách TRANG có thật — nên `unit_ids` biết
trước và `verify.py` kiểm được trích dẫn bằng code. Chat là con đường duy nhất
không có tính chất đó, và nó dùng `retrieve.py` chứ không dùng file này.

Năm scope, đơn vị nhỏ nhất là một TRANG:
    page       một trang        (target_id = "6")
    pages      khoảng trang     (target_id = "5-12")
    section    một mục          (target_id = "ch02-s03")
    chapter    một chương       (target_id = "ch02")
    document   toàn tài liệu

`pages` là scope duy nhất KHÔNG tương ứng một đơn vị có thật trong tài liệu —
nó tồn tại vì người dùng nói "tóm tắt trang 5 đến 12", và khoảng đó thường không
trùng ranh giới chương/mục nào. Bù lại nó vẫn quy về một danh sách trang, nên
`unit_ids` vẫn biết trước và `verify.py` vẫn kiểm được y như các scope khác.
"""

from __future__ import annotations

import re

from . import outline as outline_lib
from .config import settings
from .errors import AppError, BudgetExceeded, NoGroundedSource
from .models import Document, Page, Scope, ScopeContext

_CHARS_PER_TOKEN = 3  # tiếng Việt có dấu, ước lượng thô — chỉ dùng để CHỌN chiến lược
_INT_RE = re.compile(r"\d+")


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def resolve(doc: Document, scope: Scope, target_id: str | None = None) -> ScopeContext:
    """Trả văn bản của scope + chiến lược `direct`/`map_reduce`.

    KHÔNG BAO GIỜ tự cắt bớt văn bản cho vừa cửa sổ: cắt bớt = tóm tắt thiếu mà
    người dùng không hề biết. Vượt `MAX_DIRECT_TOKENS` thì đổi CHIẾN LƯỢC
    (map-reduce), không đổi nội dung.
    """
    cfg = settings()
    if scope == "page":
        return _resolve_page(doc, target_id, cfg)
    if scope in ("pages", "section", "chapter", "document"):
        return _resolve_range(doc, scope, target_id, cfg)
    raise AppError(user_message=f"Phạm vi '{scope}' không hợp lệ.")


def _resolve_page(doc: Document, target_id: str | None, cfg) -> ScopeContext:
    page_no = _as_page_no(target_id)
    page = doc.page(page_no)
    if page is None:
        raise AppError(user_message=f"Không có trang {page_no} trong tài liệu.")

    if page.char_count < cfg.min_chars_per_page:
        raise NoGroundedSource(
            user_message=f"Trang {page_no} chủ yếu là hình — mình không đọc được nội dung "
                         f"trong ảnh, nên không tóm tắt để tránh nói sai."
        )

    est = estimate_tokens(page.text)
    return ScopeContext(
        scope="page",
        target_id=str(page_no),
        unit_ids=_unit_ids([page]),
        text=page.text,
        est_tokens=est,
        strategy="direct" if est <= cfg.max_direct_tokens else "map_reduce",
        annotated_text=_annotate([page]),
    )


def _resolve_range(doc: Document, scope: Scope, target_id: str | None, cfg) -> ScopeContext:
    """section / chapter / document — cùng một đường, chỉ khác cách lấy khoảng trang."""
    pages = pages_in_scope(doc, scope, target_id)
    if not pages:
        raise AppError(user_message=f"Phạm vi '{target_id or scope}' không có trang nào.")

    readable = [p for p in pages if p.char_count >= cfg.min_chars_per_page]
    if not readable:
        raise NoGroundedSource(
            user_message=f"{scope_label(doc, scope, target_id)} gồm {len(pages)} trang nhưng "
                         f"trang nào cũng chủ yếu là hình — mình không đọc được nội dung "
                         f"trong ảnh, nên không tóm tắt để tránh nói sai."
        )

    text = "\n\n".join(p.text for p in readable)
    annotated = _annotate(readable)
    return ScopeContext(
        scope=scope,
        target_id=target_id,
        unit_ids=_unit_ids(readable),
        text=text,
        est_tokens=estimate_tokens(annotated),  # ước lượng trên bản THẬT SỰ gửi đi
        strategy="direct" if estimate_tokens(annotated) <= cfg.max_direct_tokens else "map_reduce",
        annotated_text=annotated,
    )


def _annotate(pages: list[Page]) -> str:
    """Bản gửi cho model: mỗi trang một nhãn `[trang N]`, mỗi khối một id `(p06-b03)`.

    Vẫn giữ id khối sau khi bỏ bôi đen, vì nó phục vụ chiều ngược lại: `verify.py`
    đối chiếu `anchor.block_ids` vào `unit_ids` để bắt neo trỏ ra ngoài phạm vi.
    Bỏ id đi thì model chỉ neo được số trang, và một trích dẫn bịa trong đúng
    trang đó sẽ không còn gì bắt được ngoài so khớp chuỗi.
    """
    parts: list[str] = []
    for page in pages:
        if not page.blocks:
            continue
        lines = "\n".join(f"({b.block_id}) {b.text}" for b in page.blocks)
        parts.append(f"[trang {page.page_no}]\n{lines}")
    return "\n\n".join(parts)


# --- Tra cứu phạm vi: dùng chung cho tools/, UI và eval ---

def pages_in_scope(doc: Document, scope: Scope, target_id: str | None = None) -> list[Page]:
    """Danh sách trang thuộc phạm vi, theo đúng thứ tự tài liệu."""
    if scope == "document":
        return list(doc.pages)
    if scope == "page":
        page = doc.page(_as_page_no(target_id))
        return [page] if page else []

    first, last = _page_range(doc, scope, target_id)
    if first is None:
        return []
    return [p for p in doc.pages if first <= p.page_no <= last]


def parse_page_range(target: str | None) -> tuple[int, int] | None:
    """'5-12' → (5, 12). Nguồn sự thật DUY NHẤT cho cách đọc target của scope `pages`.

    Dùng chung bởi `scope.py`, `tools/quiz.py` và `agent_core/intent.py` — ba chỗ
    đọc lệch nhau thì "trang 5 đến 12" ra ba phạm vi khác nhau, và không chỗ nào
    báo lỗi.

    Số ngược ('12-5') được đảo lại chứ không bị từ chối: đó là số học, không phải
    ý định mơ hồ. Một số duy nhất ('7') coi như khoảng một trang.
    """
    numbers = [int(n) for n in _INT_RE.findall(str(target or ""))]
    if not numbers:
        return None
    first, last = numbers[0], (numbers[1] if len(numbers) > 1 else numbers[0])
    return (last, first) if first > last else (first, last)


def _page_range(doc: Document, scope: Scope, target_id: str | None) -> tuple[int | None, int]:
    if scope == "pages":
        span = parse_page_range(target_id)
        return span if span else (None, 0)
    if scope == "chapter":
        chapter = outline_lib.find_chapter(doc.chapters, target_id or "")
        return (chapter.page_range[0], chapter.page_range[1]) if chapter else (None, 0)
    if scope == "section":
        section = outline_lib.find_section(doc.chapters, target_id or "")
        return (section.page_range[0], section.page_range[1]) if section else (None, 0)
    return (None, 0)


def scope_label(doc: Document, scope: Scope, target_id: str | None = None) -> str:
    """Nhãn người đọc được — đi thẳng vào prompt và vào tiêu đề panel."""
    if scope == "document":
        return f"Toàn bộ tài liệu ({len(doc.pages)} trang)"
    if scope == "page":
        return f"Trang {_as_page_no(target_id)}"
    if scope == "pages":
        span = parse_page_range(target_id)
        return f"Trang {span[0]}-{span[1]}" if span else "Khoảng trang"
    return outline_lib.unit_label(doc.chapters, target_id or "")


def _unit_ids(pages: list[Page]) -> list[str]:
    """Id trang VÀ id khối trong phạm vi — `verify.py` đối chiếu anchor vào đây."""
    ids: list[str] = []
    for page in pages:
        ids.append(f"p{page.page_no:02d}")
        ids.extend(b.block_id for b in page.blocks)
    return ids


def page_list_label(ctx: ScopeContext) -> str:
    """'6, 7, 8' — đưa vào prompt để model biết được phép neo vào trang nào."""
    numbers = sorted({int(uid[1:]) for uid in ctx.unit_ids if len(uid) == 3 and uid[0] == "p"})
    return ", ".join(str(n) for n in numbers)


def _as_page_no(target_id: str | None) -> int:
    try:
        return int(str(target_id)) if target_id is not None else 1
    except ValueError:
        return 1


# --- Map-reduce: chia việc trước khi gọi model ---

def plan_map_reduce(doc: Document, scope: Scope, target_id: str | None = None) -> list[int]:
    """Trang nào cần tóm tắt ở tầng dưới trước khi reduce.

    Chỉ trả trang ĐỌC ĐƯỢC: trang toàn hình không có gì để map, và đưa nó vào
    kế hoạch chỉ tạo một lời gọi chắc chắn abstain — tốn tiền, tốn thời gian
    chờ, không thêm thông tin.

    Vượt `MAX_JOB_CALLS` thì ném `BudgetExceeded` để UI HỎI TRƯỚC, chứ không
    lặng lẽ đốt 200 lời gọi rồi mới báo.
    """
    cfg = settings()
    pages = [
        p.page_no for p in pages_in_scope(doc, scope, target_id)
        if p.char_count >= cfg.min_chars_per_page
    ]
    if len(pages) > cfg.max_job_calls:
        raise BudgetExceeded(
            user_message=f"Phạm vi này có {len(pages)} trang đọc được, vượt trần "
                         f"{cfg.max_job_calls} lời gọi một job. Chọn phạm vi hẹp hơn, "
                         f"hoặc tăng MAX_JOB_CALLS trong .env nếu bạn chấp nhận chi phí."
        )
    return pages


def estimate_job(doc: Document, scope: Scope, target_id: str | None = None) -> dict:
    """Báo trước cho người dùng: bao nhiêu trang, bao nhiêu lời gọi, khoảng bao lâu.

    Con số thời gian là ước lượng thô (~2.5s/lời gọi, chạy 4 luồng) — đủ để
    người dùng quyết định có bấm hay không, đó là toàn bộ mục đích của nó.
    """
    pages = pages_in_scope(doc, scope, target_id)
    readable = [p for p in pages if p.char_count >= settings().min_chars_per_page]
    calls = len(readable) + 1  # map từng trang + một lượt reduce
    return {
        "pages": len(pages),
        "readable_pages": len(readable),
        "calls": calls,
        "seconds": max(3, round(calls * 2.5 / 4)),
    }
