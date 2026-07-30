"""Tóm tắt một phạm vi — 5 tầng dùng chung một hợp đồng và một verifier.

    page · pages                   một lời gọi
    section · chapter · document   vượt MAX_DIRECT_TOKENS thì map-reduce:
                                   tóm tắt từng trang (có cache) rồi gộp lên

Điểm quan trọng của map-reduce ở đây: bước gộp vẫn KIỂM TRÍCH DẪN VÀO VĂN BẢN
GỐC, không kiểm vào bản tóm tắt tầng dưới. Kiểm vào tầng dưới thì một câu bịa ở
tầng trang sẽ được hợp thức hoá lên tầng chương, và neo `[trang N]` biến thành
neo về một bản tóm tắt chứ không phải về slide.

Tầng dưới dùng lại cache: tóm tắt cả tài liệu sau khi đã xem vài trang chỉ tốn
phần còn thiếu.

Mức tự động hoá: AUTOMATE — mỗi bullet có neo nguồn, người dùng bấm "xem chỗ
này" là kiểm được ngay, nên sai thì sửa rẻ.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import providers
from agent_core import cache, prompting, verify
from agent_core import scope as scope_lib
from agent_core.config import settings
from agent_core.log import trace
from agent_core.models import Document, Scope, ScopeContext
from agent_core.schemas import SUMMARY_SCHEMA, bullets_range

PROMPT_ID = "summarize"
KIND = "summaries"
MAX_WORKERS = 4  # đủ nhanh mà không đụng rate limit của tài khoản dùng thử

Progress = Callable[[int, int, str], None]


def summarize(
    doc: Document,
    scope: Scope,
    target_id: str | None = None,
    *,
    force: bool = False,
    progress: Progress | None = None,
) -> dict:
    """Trả payload theo SUMMARY_SCHEMA + khoá `_meta`, đã qua verify.

    `force=True` bỏ qua cache — dùng cho nút "sinh lại".
    `progress(done, total, label)` chỉ được gọi từ luồng chính nên an toàn với Streamlit.
    """
    ctx = scope_lib.resolve(doc, scope, target_id)
    tier = "main" if scope in ("chapter", "document") else "fast"
    version = prompting.load(PROMPT_ID).version
    key = cache.content_key(ctx.text, PROMPT_ID, version, settings().model_for(tier), scope)

    if not force:
        cached = cache.load_artifact(doc.doc_hash, KIND, key)
        if cached:
            cached.setdefault("_meta", {})["cached"] = True
            return cached

    label = scope_lib.scope_label(doc, scope, target_id)
    if _needs_map_reduce(ctx):
        payload, calls, warnings = _map_reduce(doc, ctx, label, progress)
    else:
        payload, calls, warnings = _direct(ctx, label, tier), 1, []

    payload = _finalize(payload, ctx, label, calls, warnings, version, tier)
    cache.save_artifact(doc.doc_hash, KIND, key, payload)
    return payload


def _needs_map_reduce(ctx: ScopeContext) -> bool:
    """Một trang đơn lẻ không chia nhỏ được nữa — dù dài cũng gọi thẳng."""
    return ctx.strategy == "map_reduce" and ctx.scope in ("section", "chapter", "document")


def _direct(ctx: ScopeContext, label: str, tier: str) -> dict:
    n_min, n_max = bullets_range(ctx.scope)
    result = providers.complete_json(
        PROMPT_ID,
        {
            # prompt_text có nhãn trang + id khối để model đặt anchor đúng;
            # verify vẫn so quote vào ctx.text sạch.
            "source_text": ctx.prompt_text,
            "context_text": ctx.context_text,
            "scope_label": label,
            "n_bullets_min": str(n_min),
            "n_bullets_max": str(n_max),
            "page_list": scope_lib.page_list_label(ctx),
        },
        SUMMARY_SCHEMA,
        "summary",
        tier=tier,
    )
    return result.data


def _map_reduce(doc: Document, ctx: ScopeContext, label: str,
                progress: Progress | None) -> tuple[dict, int, list[str]]:
    """Map từng trang (song song, có cache) → reduce một lượt."""
    page_nos = scope_lib.plan_map_reduce(doc, ctx.scope, ctx.target_id)
    children = summarize_pages(doc, page_nos, progress=progress)

    warnings: list[str] = []
    missing = [n for n in page_nos if n not in children]
    if missing:
        warnings.append(f"không tóm tắt được {len(missing)} trang: {_compact(missing)}")

    if not children:
        return (
            {
                "scope_label": label,
                "tldr": "",
                "bullets": [],
                "key_terms": [],
                "not_covered": [f"Không trang nào trong {label} đọc được nội dung."],
                "confidence": "low",
            },
            len(page_nos),
            warnings,
        )

    if progress:
        progress(len(page_nos) + 1, len(page_nos) + 1, "Đang gộp lại")

    n_min, n_max = bullets_range(ctx.scope)
    result = providers.complete_json(
        PROMPT_ID,
        {
            # Nguồn của bước gộp là tóm tắt tầng dưới — nhưng quote trong đó đều
            # là nguyên văn slide, nên verify vào văn bản gốc vẫn khớp.
            "source_text": _children_as_source(children),
            "context_text": "",
            "scope_label": label,
            "n_bullets_min": str(n_min),
            "n_bullets_max": str(n_max),
            "page_list": scope_lib.page_list_label(ctx),
        },
        SUMMARY_SCHEMA,
        "summary",
        tier="main",  # bước gộp là nơi sai thì đau nhất: luôn dùng model chính
    )
    return result.data, len(children) + 1, warnings


def summarize_pages(doc: Document, page_nos: list[int], *,
                    progress: Progress | None = None) -> dict[int, dict]:
    """Tầng dưới của map-reduce — song song, mỗi trang một cache riêng.

    KHÔNG gọi `st.*` trong thread: thread chỉ trả dữ liệu, `progress` chạy ở
    luồng chính khi từng future hoàn thành.
    """
    out: dict[int, dict] = {}
    total = len(page_nos) + 1  # +1 cho bước gộp, để tiến độ không nhảy 100% sớm
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {page_no: pool.submit(_summarize_page_safe, doc, page_no)
                   for page_no in page_nos}
        for index, (page_no, future) in enumerate(futures.items(), start=1):
            payload = future.result()
            if payload is not None:
                out[page_no] = payload
            if progress:
                progress(index, total, f"Trang {page_no}")
    return out


def _summarize_page_safe(doc: Document, page_no: int) -> dict | None:
    """Một trang hỏng không được làm chết cả job 40 trang."""
    try:
        return summarize(doc, "page", str(page_no))
    except Exception as exc:
        trace("verify_fail", stage="map", page_no=page_no, error=str(exc)[:200])
        return None


def _children_as_source(children: dict[int, dict]) -> str:
    """Tóm tắt tầng dưới, giữ nguyên `[trang N]` và quote để bước gộp neo lại được."""
    parts: list[str] = []
    for page_no in sorted(children):
        payload = children[page_no]
        lines = [f"[trang {page_no}] {payload.get('tldr', '')}".strip()]
        for bullet in payload.get("bullets") or []:
            anchor = bullet.get("anchor") or {}
            blocks = ", ".join(anchor.get("block_ids") or [])
            lines.append(
                f"- {bullet.get('text', '')}\n"
                f"  nguồn: trang {anchor.get('page_no', page_no)}"
                f"{f' · khối {blocks}' if blocks else ''}\n"
                f"  trích: \"{anchor.get('quote', '')}\""
            )
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _finalize(payload: dict, ctx: ScopeContext, label: str, calls: int,
              warnings: list[str], version: str, tier: str) -> dict:
    """Kiểm từng bullet, loại cái không có căn cứ, gắn `_meta` cho UI.

    Loại BULLET chứ không loại cả bản tóm tắt: một bullet bịa giữa bốn bullet
    đúng thì bỏ đúng cái sai vẫn còn giá trị, ném hết đi thì người dùng không
    nhận được gì.
    """
    kept: list[dict] = []
    dropped: list[str] = []
    for bullet in payload.get("bullets") or []:
        check = verify.check_bullet(bullet, ctx)
        warnings.extend(check.warnings)
        if check.passed:
            kept.append(bullet)
        else:
            dropped.append("; ".join(check.reasons))
            trace("verify_fail", stage="summary", scope=ctx.scope,
                  target_id=ctx.target_id, reasons=check.reasons)

    payload["bullets"] = kept
    payload["scope_label"] = label

    if dropped:
        warnings.append(f"loại {len(dropped)} bullet không khớp nguồn")
    if not kept:
        payload["confidence"] = "low"
        payload["not_covered"] = list(payload.get("not_covered") or []) + [
            "Không bullet nào trong bản sinh ra kiểm được về nguồn."
        ]

    warnings.extend(verify.check_summary(payload, ctx).warnings)

    payload["_meta"] = {
        "scope": ctx.scope,
        "target_id": ctx.target_id,
        "scope_label": label,
        "unit_ids": ctx.unit_ids,
        "strategy": ctx.strategy,
        "calls": calls,
        "cached": False,
        "prompt_version": version,
        "model": settings().model_for(tier),
        "dropped_bullets": len(dropped),
        "warnings": warnings,
    }
    return payload


def _compact(numbers: list[int]) -> str:
    return ", ".join(str(n) for n in numbers[:8]) + (" …" if len(numbers) > 8 else "")
