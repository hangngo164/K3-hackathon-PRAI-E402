"""Phán quyết route của model: chạy được, hay phải hỏi lại.

`tools/router.py` nhận một `Route` từ model — đó là ĐỀ XUẤT, chưa phải quyết
định. File này đối chiếu đề xuất vào `Document` thật rồi trả `Plan`:

    Route (model đề xuất)  →  resolve_route()  →  Plan(kind = tool | clarify | explain)

Vì sao tách hẳn khỏi `tools/router.py`: model trả `ch07` trên tài liệu có 2
chương, hoặc trang 60 trên deck 30 trang, là chuyện sẽ xảy ra. Tin route thì lỗi
đó nổ giữa `scope.resolve()` dưới dạng exception khó đọc — hoặc tệ hơn, chạy êm
trên phạm vi sai. Kiểm ở đây thì mọi route sai quy về đúng một hành vi: hỏi lại,
kèm những lựa chọn CÓ THẬT trong tài liệu.

Module thuần logic: không gọi model, không import `streamlit`, không import
`providers`. Nhờ vậy cả bảng route đúng/sai test được bằng dữ liệu bịa, không
tốn một lời gọi nào — đây là lý do phần kiểm nằm ở `agent_core/` chứ không nằm
cạnh phần gọi model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, get_args

from . import outline as outline_lib
from . import scope as scope_lib  # chỉ dùng parse_page_range: một cách đọc "5-12" duy nhất
from .models import Document, Scope
from .retrieve import fold  # tiện ích bỏ dấu — người dùng gõ "chuong 2" không dấu là bình thường

VALID_SCOPES: tuple[str, ...] = get_args(Scope)
INTENTS: tuple[str, ...] = ("summarize", "quiz", "ask", "explain_quiz", "clarify")

# Số câu quiz: mặc định do CODE chọn (cùng lý lẽ với `schemas.bullets_range` —
# đây là quyết định sản phẩm, không phải việc model đoán ý người dùng).
# Người dùng nói rõ một con số thì TÔN TRỌNG con số đó, chỉ chặn ở trần trên.
_ITEMS_DEFAULT_DOCUMENT = 12  # yêu cầu: quiz toàn tài liệu ~10-20 câu
_ITEMS_DEFAULT_PART = 5       # yêu cầu: quiz một phần ~3-7 câu
_ITEMS_MAX = 20

_MAX_CLARIFY_OPTIONS = 4  # nhiều hơn thì bảng lựa chọn thành một cây outline thứ hai
_FIRST_INT_RE = re.compile(r"\d+")


@dataclass(frozen=True)
class Route:
    """Nguyên văn đề xuất của model, đã parse an toàn về đúng kiểu."""

    intent: str = ""
    scope: str = ""
    target: str = ""
    n_items: int = 0
    question: str = ""
    options: list[str] = field(default_factory=list)
    item_no: int = 0
    rationale: str = ""


@dataclass(frozen=True)
class UIContext:
    """Thứ code biết mà model không được tự đoán: người dùng đang ở đâu.

    Truyền vào thay vì để model suy ra từ hội thoại, vì đây là sự thật của phiên
    làm việc — "trang này" phải là trang đang mở thật, không phải trang mà model
    nhớ là đang mở.
    """

    page_no: int = 1
    quiz_items: int = 0  # số câu của bộ quiz đang mở; 0 = chưa có bộ nào
    last_scope: tuple[str, str | None] | None = None  # phạm vi của lượt trước — cho "phần đó"


@dataclass(frozen=True)
class Plan:
    """Phán quyết của code. `kind` quyết định app làm gì tiếp.

        tool     gọi `tools.registry.run(tool, ...)`
        clarify  hỏi lại một câu, kèm `options` bấm được
        explain  trả lời từ bộ quiz đang mở, KHÔNG gọi model
    """

    kind: Literal["tool", "clarify", "explain"]
    tool: str = ""
    scope: str = ""
    target_id: str | None = None
    n_items: int = 0
    question: str = ""
    options: list[str] = field(default_factory=list)
    item_no: int = 0
    rationale: str = ""


def route_from_dict(raw: dict, rationale_fallback: str = "") -> Route:
    """JSON của model → Route. Field thiếu/sai kiểu về giá trị an toàn.

    Không ném lỗi ở đây: một route méo phải đi tiếp tới `resolve_route()` để
    thành một câu hỏi lại tử tế, chứ không thành một traceback.
    """
    options = raw.get("options") or []
    if not isinstance(options, list):
        options = []
    return Route(
        intent=str(raw.get("intent", "") or "").strip(),
        scope=str(raw.get("scope", "") or "").strip(),
        target=str(raw.get("target", "") or "").strip(),
        n_items=_as_int(raw.get("n_items")),
        question=str(raw.get("question", "") or "").strip(),
        options=[str(o).strip() for o in options if str(o).strip()],
        item_no=_as_int(raw.get("item_no")),
        rationale=str(raw.get("rationale", "") or "").strip() or rationale_fallback,
    )


def resolve_route(doc: Document, route: Route, ui: UIContext) -> Plan:
    """Cửa duy nhất biến đề xuất của model thành việc được phép chạy."""
    if route.intent == "clarify":
        return _clarify(
            route.question or "Bạn muốn mình làm gì với tài liệu này?",
            route.options,
            route.rationale,
        )

    if route.intent == "explain_quiz":
        return _resolve_explain(route, ui)

    if route.intent == "ask":
        # Câu hỏi rỗng là dấu hiệu model phân loại nhầm chứ không phải người dùng
        # gõ rỗng (app đã chặn chuỗi rỗng trước khi gọi router).
        if not route.question:
            return _clarify("Bạn muốn hỏi gì về tài liệu này?", [], route.rationale)
        return _resolve_ask(doc, route, ui)

    if route.intent in ("summarize", "quiz"):
        return _resolve_scoped(doc, route, ui)

    return _clarify(
        "Mình chưa rõ bạn muốn gì. Mình làm được ba việc trên tài liệu này: "
        "tóm tắt một phạm vi, tạo quiz để bạn tự kiểm, hoặc trả lời câu hỏi về nội dung.",
        ["Tóm tắt trang này", "Tạo quiz trang này"],
        route.rationale,
    )


# --- ask: phạm vi là TUỲ CHỌN, khác hẳn summarize/quiz ---

def _resolve_ask(doc: Document, route: Route, ui: UIContext) -> Plan:
    """Chỉ thu hẹp vùng tìm khi câu hỏi tự nêu phạm vi.

    KHÔNG suy ra phạm vi ngầm định như summarize/quiz: "attention là gì" phải
    được tìm trên cả tài liệu. Bó nó về trang đang xem chỉ vì người dùng tình cờ
    đang mở trang đó là cách chắc chắn nhất để trả "không tìm thấy" trên một tài
    liệu có nói về attention ở trang khác.
    """
    if not route.scope:
        return Plan(kind="tool", tool="ask", question=route.question, rationale=route.rationale)

    scope, target_id, problem = resolve_scope(doc, route.scope, route.target, ui)
    if problem is not None:
        return _clarify(problem[0], problem[1], route.rationale)
    return Plan(kind="tool", tool="ask", scope=scope, target_id=target_id,
                question=route.question, rationale=route.rationale)


# --- summarize / quiz: phải chốt được một phạm vi có thật ---

def _resolve_scoped(doc: Document, route: Route, ui: UIContext) -> Plan:
    scope, target_id, problem = resolve_scope(doc, route.scope, route.target, ui)
    if problem is not None:
        return _clarify(problem[0], problem[1], route.rationale)

    n_items = 0
    if route.intent == "quiz":
        n_items = route.n_items if route.n_items > 0 else _default_items(scope)
        n_items = max(1, min(_ITEMS_MAX, n_items))

    return Plan(
        kind="tool",
        tool=route.intent,
        scope=scope,
        target_id=target_id,
        n_items=n_items,
        rationale=route.rationale,
    )


def _default_items(scope: str) -> int:
    return _ITEMS_DEFAULT_DOCUMENT if scope == "document" else _ITEMS_DEFAULT_PART


Problem = tuple[str, list[str]]  # (câu hỏi lại, các lựa chọn bấm được)


def resolve_scope(
    doc: Document, scope: str, target: str, ui: UIContext
) -> tuple[str, str | None, Problem | None]:
    """(scope, target) thô → (scope, target_id) có thật, hoặc một Problem.

    Tách thành hàm công khai để `eval/` và test gọi trực tiếp được: đây là chỗ
    quyết định "route này chạy trên phạm vi nào", và nó phải đo được riêng khỏi
    phần gọi model.
    """
    # Không nói phạm vi ⇒ lấy trang người dùng đang đứng. Không phải đoán: "tóm
    # tắt trang này" là câu hoàn chỉnh khi trang đang mở là một sự thật của phiên.
    scope = scope or "page"

    if scope not in VALID_SCOPES:
        return "", None, (
            f"Mình chưa hiểu phạm vi '{scope}'. Bạn muốn làm trên phạm vi nào?",
            _scope_options(doc, ui),
        )

    if scope == "document":
        return "document", None, None

    if scope == "page":
        return _resolve_page(doc, target, ui)

    if scope == "pages":
        return _resolve_pages(doc, target, ui)

    return _resolve_unit(doc, scope, target, ui)


def _resolve_page(doc: Document, target: str, ui: UIContext) -> tuple[str, str | None, Problem | None]:
    total = len(doc.pages)
    if not target:
        return "page", str(ui.page_no), None  # "tóm tắt trang này"

    match = _FIRST_INT_RE.search(target)
    if not match:
        return "", None, (
            f"Mình chưa đọc được số trang từ '{target}'. Tài liệu này có {total} trang — "
            f"bạn muốn trang nào?",
            [f"Trang {ui.page_no} (đang xem)", "Toàn bộ tài liệu"],
        )

    page_no = int(match.group(0))
    if doc.page(page_no) is None:
        return "", None, (
            f"Tài liệu này chỉ có {total} trang nên không có trang {page_no}.",
            [f"Trang {ui.page_no} (đang xem)", f"Trang {total} (trang cuối)"],
        )
    return "page", str(page_no), None


def _resolve_pages(doc: Document, target: str,
                   ui: UIContext) -> tuple[str, str | None, Problem | None]:
    """'5-12' → scope `pages`. Khoảng vượt ra ngoài tài liệu thì HỎI, không tự cắt.

    Cắt hộ ('5-100' trên deck 30 trang ⇒ 5-30) là cách hiểu hợp lý nhất, nhưng nó
    vẫn là một giả định — và giả định im lặng ở đây làm người dùng tưởng đã tóm
    tắt tới trang 100. Nên vẫn hỏi, nhưng đưa sẵn khoảng đã cắt thành một nút để
    đồng ý chỉ mất một cú bấm.
    """
    total = len(doc.pages)
    span = scope_lib.parse_page_range(target)
    if span is None:
        return "", None, (
            f"Mình chưa đọc được khoảng trang từ '{target}'. Tài liệu có {total} trang — "
            f"bạn muốn từ trang nào đến trang nào?",
            [f"Trang {ui.page_no} (đang xem)", "Toàn bộ tài liệu"],
        )

    first, last = span
    if first == last:
        return _resolve_page(doc, str(first), ui)  # "trang 7 đến 7" chỉ là trang 7

    if first < 1 or last > total:
        clipped_first, clipped_last = max(1, first), min(total, last)
        options = ["Toàn bộ tài liệu"]
        if clipped_first < clipped_last:
            options.insert(0, f"Trang {clipped_first} đến {clipped_last}")
        return "", None, (
            f"Tài liệu này có {total} trang nên không có khoảng {first}-{last}.",
            options,
        )

    return "pages", f"{first}-{last}", None


def _resolve_unit(doc: Document, scope: str, target: str,
                  ui: UIContext) -> tuple[str, str | None, Problem | None]:
    """chapter / section: target phải là `unit_id` có thật, hoặc một tiêu đề khớp DUY NHẤT."""
    if not doc.chapters:
        return "", None, (
            "Tài liệu này không tách được chương/mục, nên mình chỉ làm theo trang, "
            "khoảng trang, hoặc toàn bộ tài liệu.",
            [f"Trang {ui.page_no} (đang xem)", "Toàn bộ tài liệu"],
        )

    if target:
        if scope == "chapter" and outline_lib.find_chapter(doc.chapters, target):
            return "chapter", target, None
        if scope == "section" and outline_lib.find_section(doc.chapters, target):
            return "section", target, None

        # Model trả tiêu đề thay vì unit_id, hoặc người dùng gõ thẳng tên mục
        # ("phần giới thiệu"). Khớp theo tên là việc của CODE, và chỉ nhận khi
        # khớp đúng một đơn vị — hai đơn vị cùng khớp thì phải hỏi lại.
        matched = match_by_title(doc, target)
        if len(matched) == 1:
            return matched[0][0], matched[0][1], None
        if len(matched) > 1:
            return "", None, (
                f"'{target}' khớp với {len(matched)} phần trong tài liệu. Bạn muốn phần nào?",
                [label for _, _, label in matched[:_MAX_CLARIFY_OPTIONS]],
            )

    known = "Chưa có" if not target else f"Mình không tìm thấy '{target}' trong tài liệu"
    return "", None, (
        f"{known}. Cây chương/mục của tài liệu này như sau — bạn chọn giúp mình.",
        _unit_options(doc),
    )


def match_by_title(doc: Document, text: str) -> list[tuple[str, str, str]]:
    """Tìm chương/mục theo TÊN. Trả [(scope, unit_id, nhãn)] — có thể rỗng hoặc nhiều.

    Bỏ dấu cả hai phía trước khi so: rất nhiều người gõ "chuong 2" hoặc
    "positional encoding" không dấu, và trượt vì thiếu dấu thì trượt hoàn toàn.
    Khớp hai chiều (tên chứa câu vào, hoặc câu vào chứa tên) vì người dùng gõ cả
    "giới thiệu" cho mục "1. Giới thiệu chung" và ngược lại.
    """
    needle = fold(text).strip()
    if not needle:
        return []

    found: list[tuple[str, str, str]] = []
    for chapter in doc.chapters:
        if _title_hit(needle, chapter.title):
            found.append(("chapter", chapter.unit_id,
                          outline_lib.unit_label(doc.chapters, chapter.unit_id)))
        for section in chapter.sections:
            if _title_hit(needle, section.title):
                found.append(("section", section.unit_id,
                              outline_lib.unit_label(doc.chapters, section.unit_id)))
    return found


def _title_hit(needle: str, title: str) -> bool:
    hay = fold(title).strip()
    if not hay:
        return False
    return needle == hay or needle in hay or hay in needle


def _unit_options(doc: Document) -> list[str]:
    options = [c.title for c in doc.chapters[:_MAX_CLARIFY_OPTIONS]]
    return options or ["Toàn bộ tài liệu"]


def _scope_options(doc: Document, ui: UIContext) -> list[str]:
    options = [f"Trang {ui.page_no} (đang xem)", "Toàn bộ tài liệu"]
    if doc.chapters:
        options.insert(1, doc.chapters[0].title)
    return options[:_MAX_CLARIFY_OPTIONS]


# --- explain_quiz: trả lời từ bộ quiz đang mở, không gọi model ---

def _resolve_explain(route: Route, ui: UIContext) -> Plan:
    """Vì sao không đẩy sang `ask`: câu quiz ĐÃ có `explanation` + `quote` đã qua
    verify. Gọi model lần nữa để giải thích lại chỉ thêm một chỗ bịa được, trong
    khi câu trả lời đúng đang nằm sẵn trong payload.
    """
    if ui.quiz_items <= 0:
        return _clarify(
            "Hiện chưa có bộ quiz nào đang mở nên mình chưa biết bạn hỏi câu nào.",
            [f"Tạo quiz trang {ui.page_no}", "Tạo quiz toàn bộ tài liệu"],
            route.rationale,
        )
    if not 1 <= route.item_no <= ui.quiz_items:
        return _clarify(
            f"Bộ quiz đang mở có {ui.quiz_items} câu, nên mình chưa rõ bạn hỏi câu số mấy.",
            [f"Câu {n}" for n in range(1, min(ui.quiz_items, _MAX_CLARIFY_OPTIONS) + 1)],
            route.rationale,
        )
    return Plan(kind="explain", item_no=route.item_no, rationale=route.rationale)


def _clarify(question: str, options: list[str], rationale: str = "") -> Plan:
    return Plan(
        kind="clarify",
        question=question,
        options=[o for o in options if o][:_MAX_CLARIFY_OPTIONS],
        rationale=rationale,
    )


def _as_int(value: object) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0
