"""Sinh câu hỏi ôn tập có neo nguồn, cân hạn ngạch, chạy vòng kiểm-sửa.

Ba đường vào, cùng một hợp đồng:
    page / pages                một lời gọi
    section / chapter           một lời gọi, hoặc chia nhỏ nếu xin nhiều câu
    document                    LUÔN chia theo chương/mục rồi trộn

Vì sao quiz cả tài liệu phải chia nhỏ thay vì nhồi 40 trang vào một prompt:
nhồi cả tài liệu thì model bám vào vài trang đầu và câu hỏi loãng dần — nó
không có cách nào biết "đã hỏi đủ đều chưa". Chia hạn ngạch TRƯỚC khi sinh biến
việc phủ đều thành phép chia của code, không phải thiện chí của model.

Mức tự động hoá: AUGMENT — đáp án sai dạy người học kiến thức sai ngay trước kỳ
đánh giá, sửa rất đắt. Nên mọi câu luôn kèm trích dẫn để người dùng tự kiểm, và
câu không qua verify thì bị loại chứ không hiển thị kèm cảnh báo.
"""

from __future__ import annotations

import random
from typing import Callable

import providers
from agent_core import cache, prompting, verify
from agent_core import scope as scope_lib
from agent_core.config import settings
from agent_core.errors import NoGroundedSource
from agent_core.log import trace
from agent_core.models import Document, Scope, ScopeContext
from agent_core.schemas import QUIZ_SCHEMA, difficulty_label

PROMPT_ID = "quiz"
KIND = "quizzes"

OVERPRODUCE = 2         # sinh dư để sau khi loại vẫn đủ số câu — rẻ hơn một vòng sinh lại
MAX_ITEMS_PER_CALL = 8  # trên ngưỡng này câu hỏi bắt đầu loãng => chia phần
MAX_PART_SHARE = 0.4    # không phần nào chiếm quá 40% số câu
_PAGES_PER_GROUP = 4    # tài liệu 'flat': gom 4 trang thành một phần
_MAX_AVOID_FACTS = 40   # đủ để model biết đã hỏi gì, chưa đủ để đẩy nguồn ra khỏi prompt
_MAX_VARIANTS = 20      # quá chừng này bộ thì nguồn đã cạn ý, không phải thiếu chỗ chứa

Progress = Callable[[int, int, str], None]
Part = tuple[Scope, str | None, str]  # (scope, target_id, nhãn)


def generate(
    doc: Document,
    scope: Scope,
    target_id: str | None = None,
    n_items: int = 5,
    *,
    variant: int | None = None,
    force: bool = False,
    progress: Progress | None = None,
) -> dict:
    """Trả `{items, notes, _meta}` — mọi item đã qua verify.

    `variant` là "bộ thứ mấy cho cùng phạm vi này". Nó vào khoá cache VÀ vào
    danh sách ý phải tránh:

      · `None` (mặc định) = bộ đầu tiên CHƯA CÓ trong cache ⇒ xin quiz lần nữa
        trên cùng phạm vi luôn ra bộ khác, kể cả sau khi khởi động lại app
      · một số cụ thể = đúng bộ đó ⇒ `eval/run.py` pin `variant=0` vẫn đo lại
        được y hệt, và xin lại bộ cũ không tốn lời gọi nào

    Dò từ đĩa chứ không đếm trong `session_state`: cache là thứ quyết định người
    dùng nhận lại bộ cũ hay bộ mới, nên bộ đếm phải sống cùng chỗ với cache.

    Đa dạng ở đây đến từ việc phủ rộng tài liệu hơn, không từ việc nới ràng buộc:
    mọi câu vẫn phải qua `verify.check_quiz_item` với cùng một bộ luật.
    """
    ctx = scope_lib.resolve(doc, scope, target_id)
    version = prompting.load(PROMPT_ID).version
    tier = "main"  # quiz luôn dùng model chính: đây là chỗ sai thì đau
    model = settings().model_for(tier)

    if variant is None:
        variant = _first_unused_variant(doc, ctx, version, model, scope, n_items)
        force = True  # đã biết chắc chưa có trong cache, khỏi đọc lại một lần nữa

    key = _cache_key(ctx.text, version, model, scope, n_items, variant)

    if not force:
        cached = cache.load_artifact(doc.doc_hash, KIND, key)
        if cached:
            cached.setdefault("_meta", {})["cached"] = True
            return cached

    label = scope_lib.scope_label(doc, scope, target_id)
    avoid = _spent_facts(doc, ctx, version, model, scope, n_items, variant)
    parts = _parts_for(doc, scope, target_id)
    if parts and _should_split(scope, ctx, n_items, parts):
        payload = _generate_by_parts(doc, parts, n_items, label, progress, variant, force)
    else:
        payload = _generate_one(doc, ctx, label, n_items, avoid)

    payload["_meta"].update({
        "scope": scope,
        "target_id": target_id,
        "scope_label": label,
        "cached": False,
        "prompt_version": version,
        "model": model,
        "requested": n_items,
        "variant": variant,
        "avoided_facts": len(avoid),
    })
    cache.save_artifact(doc.doc_hash, KIND, key, payload)
    return payload


def _cache_key(ctx_text: str, version: str, model: str, scope: Scope,
               n_items: int, variant: int) -> str:
    return cache.content_key(
        ctx_text, PROMPT_ID, version, model, scope, str(n_items), str(variant)
    )


def _first_unused_variant(doc: Document, ctx: ScopeContext, version: str, model: str,
                          scope: Scope, n_items: int) -> int:
    """Bộ đầu tiên chưa có trong cache cho phạm vi này.

    Trần `_MAX_VARIANTS` không phải để tiết kiệm: qua chừng đó bộ thì tài liệu
    đã cạn ý thật, và bộ thứ 21 chỉ là hỏi lại ý cũ bằng chữ khác. Chạm trần thì
    quay lại dùng bộ cuối — người dùng nhận bộ cũ nhưng `notes` của nó đã nói rõ
    nguồn không còn gì mới.
    """
    for candidate in range(_MAX_VARIANTS):
        key = _cache_key(ctx.text, version, model, scope, n_items, candidate)
        if cache.load_artifact(doc.doc_hash, KIND, key) is None:
            return candidate
    return _MAX_VARIANTS - 1


def _spent_facts(doc: Document, ctx: ScopeContext, version: str, model: str,
                 scope: Scope, n_items: int, variant: int) -> list[str]:
    """Ý đã hỏi ở các bộ TRƯỚC của cùng phạm vi — đọc lại từ chính cache.

    Đọc từ cache chứ không giữ trong `session_state`: bộ quiz đã sinh là nguồn
    sự thật duy nhất về "đã hỏi gì", và nó sống sót qua việc restart app giữa
    buổi demo. Không có bộ nào trước ⇒ rỗng ⇒ prompt không đổi so với lượt đầu.
    """
    facts: list[str] = []
    for earlier in range(variant):
        payload = cache.load_artifact(
            doc.doc_hash, KIND,
            _cache_key(ctx.text, version, model, scope, n_items, earlier),
        )
        for item in (payload or {}).get("items") or []:
            stem = str(item.get("stem", "") or "").strip()
            if not stem:
                continue
            quote = str((item.get("anchor") or {}).get("quote", "") or "").strip()
            facts.append(f"- {stem}" + (f'  ← đã lấy từ: "{quote[:90]}"' if quote else ""))
    return facts[:_MAX_AVOID_FACTS]


def _should_split(scope: Scope, ctx: ScopeContext, n_items: int, parts: list[Part]) -> bool:
    """Chia phần khi: quiz cả tài liệu · xin nhiều câu · hoặc nguồn quá lớn cho một lời gọi."""
    if scope == "document":
        return True
    return n_items > MAX_ITEMS_PER_CALL or ctx.strategy == "map_reduce"


# --- Một lời gọi cho một phạm vi ---

def _generate_one(doc: Document, ctx: ScopeContext, label: str, n_items: int,
                  avoid: list[str] | None = None) -> dict:
    """Sinh dư → kiểm → sửa tối đa một lượt → cắt về đúng số câu."""
    avoid = avoid or []
    result = providers.complete_json(
        PROMPT_ID,
        {
            "source_text": ctx.prompt_text,
            "scope_label": label,
            "n_items": str(n_items + OVERPRODUCE),
            "difficulty_mix": difficulty_label(ctx.scope),
            "page_list": scope_lib.page_list_label(ctx),
            "avoid_facts": "\n".join(avoid),
            "repair_feedback": "",
        },
        QUIZ_SCHEMA,
        "quiz",
        tier="main",
        temperature=0.4,  # cao hơn tóm tắt: bộ câu hỏi cần đa dạng, không cần ổn định
    )

    kept, dropped, calls = _verify_and_repair(result.data.get("items") or [], ctx, label, avoid)
    kept = _dedupe(kept)[:n_items]

    return {
        "items": _renumber(kept),
        "notes": str(result.data.get("notes", "") or ""),
        "_meta": {
            "calls": 1 + calls,
            "produced": len(result.data.get("items") or []),
            "dropped": dropped,
            "parts": [{"label": label, "items": len(kept)}],
            "warnings": _shortfall_warning(len(kept), n_items, label),
        },
    }


def _verify_and_repair(items: list[dict], ctx: ScopeContext, label: str,
                       avoid: list[str] | None = None) -> tuple[list[dict], int, int]:
    """Kiểm từng câu; câu fail được sửa MỘT lượt rồi thôi.

    Một lượt chứ không phải vòng lặp: nếu model không sửa được sau khi đã được
    chỉ tận nơi sai chỗ nào, lượt thứ hai gần như chỉ đổi cách sai. Bỏ câu đó
    và nói thật số câu thực tế thì trung thực hơn.
    """
    kept: list[dict] = []
    dropped = 0
    repair_calls = 0

    for item in items:
        check = verify.check_quiz_item(item, ctx)
        if check.passed:
            kept.append(item)
            continue

        trace("verify_fail", stage="quiz", scope=ctx.scope, target_id=ctx.target_id,
              item_id=item.get("item_id"), reasons=check.reasons)
        fixed = repair(item, check.reasons, ctx, label, avoid)
        repair_calls += 1
        if fixed is not None and verify.check_quiz_item(fixed, ctx).passed:
            kept.append(fixed)
        else:
            dropped += 1

    return kept, dropped, repair_calls


def repair(item: dict, reasons: list[str], ctx: ScopeContext, label: str,
           avoid: list[str] | None = None) -> dict | None:
    """Sửa một item hỏng. Vẫn hỏng => trả None (loại câu).

    Dùng lại `prompts/quiz.v1.md` qua biến `{{repair_feedback}}` thay vì một
    prompt riêng: luật ràng buộc phải giống hệt lượt sinh đầu, tách file là mở
    đường cho hai bộ luật lệch nhau.
    """
    feedback = (
        "Câu hỏi dưới đây KHÔNG đạt. Sinh lại ĐÚNG MỘT câu thay thế, cùng phạm vi.\n"
        f"Câu hỏng: {item.get('stem', '')}\n"
        "Lỗi cần sửa:\n" + "\n".join(f"- {reason}" for reason in reasons)
    )
    try:
        result = providers.complete_json(
            PROMPT_ID,
            {
                "source_text": ctx.text,
                "scope_label": label,
                "n_items": "1",
                "difficulty_mix": difficulty_label(ctx.scope),
                "page_list": scope_lib.page_list_label(ctx),
                "avoid_facts": "\n".join(avoid or []),
                "repair_feedback": feedback,
            },
            QUIZ_SCHEMA,
            "quiz",
            tier="main",
            temperature=0.2,
        )
    except Exception as exc:
        trace("verify_fail", stage="repair", error=str(exc)[:200])
        return None
    items = result.data.get("items") or []
    return items[0] if items else None


# --- Chia phần rồi trộn ---

def _parts_for(doc: Document, scope: Scope, target_id: str | None) -> list[Part]:
    """Các phần con của một phạm vi. Rỗng = không chia nhỏ được nữa."""
    if scope == "document":
        if doc.chapters:
            return [("chapter", c.unit_id, c.title) for c in doc.chapters]
        return _page_groups(doc, [p.page_no for p in doc.pages])

    if scope == "chapter":
        chapter = next((c for c in doc.chapters if c.unit_id == target_id), None)
        if chapter and len(chapter.sections) >= 2:
            return [("section", s.unit_id, s.title) for s in chapter.sections]
        if chapter:
            first, last = chapter.page_range
            return _page_groups(doc, list(range(first, last + 1)))
        return []

    if scope == "pages":
        span = scope_lib.parse_page_range(target_id)
        return _page_groups(doc, list(range(span[0], span[1] + 1))) if span else []

    if scope == "section":
        section = next(
            (s for c in doc.chapters for s in c.sections if s.unit_id == target_id), None
        )
        if section:
            first, last = section.page_range
            pages = list(range(first, last + 1))
            return [("page", str(n), f"Trang {n}") for n in pages] if len(pages) >= 2 else []
        return []

    return []


def _page_groups(doc: Document, page_nos: list[int]) -> list[Part]:
    """Tài liệu không tách được chương/mục thì gom trang thành phần nhân tạo.

    Chỉ nhận trang ĐỌC ĐƯỢC: một nhóm toàn trang hình sẽ ném ScopeTooThin và
    chiếm mất hạn ngạch của nhóm khác.
    """
    cfg = settings()
    readable = [
        n for n in page_nos
        if (page := doc.page(n)) and page.char_count >= cfg.min_chars_per_page
    ]
    groups: list[Part] = []
    for start in range(0, len(readable), _PAGES_PER_GROUP):
        block = readable[start:start + _PAGES_PER_GROUP]
        if len(block) == 1:
            groups.append(("page", str(block[0]), f"Trang {block[0]}"))
        elif block:
            # Không có unit_id cho một nhóm trang tuỳ ý, nên mỗi nhóm đại diện
            # bằng trang đầu; phần còn lại của nhóm vào cùng lời gọi qua scope 'page'.
            groups.append(("page", str(block[0]), f"Trang {block[0]}-{block[-1]}"))
    return groups if len(groups) >= 2 else []


def allocate_quota(parts: list[Part], weights: list[int], n_items: int) -> list[int]:
    """Chia hạn ngạch câu hỏi cho từng phần TRƯỚC khi sinh.

    Ba ràng buộc, theo đúng thứ tự ưu tiên:
      1. mỗi phần có ít nhất 1 câu (khi đủ câu để chia)
      2. không phần nào vượt 40% tổng số câu
      3. phần còn lại chia theo số trang

    Thiếu (1) thì chương cuối tài liệu không bao giờ được hỏi. Thiếu (2) thì
    chương dài nhất nuốt cả bộ đề.
    """
    count = len(parts)
    if count == 0:
        return []
    if n_items <= count:
        # Không đủ câu cho mọi phần: ưu tiên phần nhiều trang nhất, mỗi phần 1 câu
        order = sorted(range(count), key=lambda i: -weights[i])[:n_items]
        return [1 if i in set(order) else 0 for i in range(count)]

    # Trần 40% chỉ áp được khi có đủ phần để chia. Với 1-2 phần thì 40% thấp hơn
    # cả mức chia đều, và hạn ngạch sẽ không bao giờ cộng đủ n_items — nên trần
    # thật là max(chia đều, 40%).
    cap = max(1, -(-n_items // count), int(n_items * MAX_PART_SHARE))
    total_weight = sum(weights) or count
    quota = [
        min(cap, max(1, int(n_items * (weights[i] or 1) / total_weight)))
        for i in range(count)
    ]

    # Cân lại phần dư/thiếu, luôn tôn trọng trần `cap`
    guard = 0
    while sum(quota) != n_items and guard < n_items * 4:
        guard += 1
        if sum(quota) < n_items:
            candidates = [i for i in range(count) if quota[i] < cap]
            if not candidates:
                break
            quota[max(candidates, key=lambda i: weights[i] / max(1, quota[i]))] += 1
        else:
            candidates = [i for i in range(count) if quota[i] > 1]
            if not candidates:
                break
            quota[min(candidates, key=lambda i: weights[i] / max(1, quota[i]))] -= 1
    return quota


def _generate_by_parts(doc: Document, parts: list[Part], n_items: int, label: str,
                       progress: Progress | None, variant: int = 0,
                       force: bool = False) -> dict:
    """Mỗi phần tự lo phần đa dạng của nó: `variant` đi xuống nguyên vẹn, nên
    "bộ thứ hai của cả tài liệu" = "bộ thứ hai của từng chương", và mỗi chương
    tự tránh ý nó đã hỏi ở bộ trước. Thiếu chỗ này thì tầng document sinh mới
    nhưng từng chương vẫn lấy nguyên bộ cũ từ cache.
    """
    weights = [len(scope_lib.pages_in_scope(doc, scope, target)) or 1
               for scope, target, _ in parts]
    quota = allocate_quota(parts, weights, n_items)

    items: list[dict] = []
    warnings: list[str] = []
    breakdown: list[dict] = []
    calls = 0
    dropped = 0

    for index, ((part_scope, part_target, part_label), want) in enumerate(zip(parts, quota), 1):
        if progress:
            progress(index, len(parts), part_label)
        if want <= 0:
            continue
        try:
            part = generate(doc, part_scope, part_target, n_items=want,
                            variant=variant, force=force)
        except NoGroundedSource as exc:
            warnings.append(f"{part_label}: {exc.user_message}")
            continue
        except Exception as exc:
            warnings.append(f"{part_label}: sinh câu hỏi hỏng ({exc})")
            trace("verify_fail", stage="quiz_part", part=part_label, error=str(exc)[:200])
            continue

        got = part.get("items") or []
        items.extend(got)
        meta = part.get("_meta") or {}
        calls += int(meta.get("calls") or 0)
        dropped += int(meta.get("dropped") or 0)
        warnings.extend(meta.get("warnings") or [])
        breakdown.append({"label": part_label, "items": len(got), "quota": want})

    items = _dedupe(items)
    # Trộn tất định theo tài liệu + variant: không đi tuần tự theo trang (làm bài
    # mà đoán được thứ tự thì không còn kiểm được mình hiểu tới đâu), nhưng CÙNG
    # một variant chạy lại vẫn ra cùng thứ tự để so sánh giữa các lượt eval.
    random.Random(f"{doc.doc_hash}:{label}:{n_items}:{variant}").shuffle(items)
    items = items[:n_items]

    warnings += _shortfall_warning(len(items), n_items, label)
    return {
        "items": _renumber(items),
        "notes": "",
        "_meta": {
            "calls": calls,
            "produced": len(items),
            "dropped": dropped,
            "parts": breakdown,
            "warnings": warnings,
        },
    }


# --- Tiện ích ---

def _dedupe(items: list[dict]) -> list[dict]:
    """Bỏ câu trùng ý: cùng stem, hoặc cùng trích dẫn nguồn.

    Trùng quote là dấu hiệu chắc chắn hơn trùng stem — hai phần khác nhau vẫn
    có thể hỏi cùng một câu bằng hai cách diễn đạt.
    """
    seen_stems: set[str] = set()
    seen_quotes: set[str] = set()
    out: list[dict] = []
    for item in items:
        stem = verify.normalize(str(item.get("stem", "")))
        quote = verify.normalize(str((item.get("anchor") or {}).get("quote", "")))
        if not stem or stem in seen_stems or (quote and quote in seen_quotes):
            continue
        seen_stems.add(stem)
        if quote:
            seen_quotes.add(quote)
        out.append(item)
    return out


def _renumber(items: list[dict]) -> list[dict]:
    """item_id phải duy nhất trong bộ: các phần con đều tự đánh 'q1'."""
    for index, item in enumerate(items, start=1):
        item["item_id"] = f"q{index}"
    return items


def _shortfall_warning(got: int, want: int, label: str) -> list[str]:
    """Nói thật khi không đủ câu — im lặng trả ít hơn là để người dùng tự đoán."""
    if got >= want:
        return []
    if got == 0:
        return [f"Không câu nào trong {label} có đủ căn cứ kiểm được về nguồn."]
    return [f"{label} chỉ đủ căn cứ cho {got}/{want} câu — mình tạo {got} câu thay vì {want}."]
