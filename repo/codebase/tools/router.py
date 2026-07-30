"""Điều phối: câu người dùng gõ → tool nào, phạm vi nào.

Đây là tool duy nhất người dùng không bấm được — nó chạy trước mọi tool khác,
mỗi lượt chat một lần:

    router.route(doc, "tóm tắt chương 2", ui, history)  →  Plan(tool="summarize", …)

Ranh giới giữa file này và `agent_core/intent.py` là ranh giới quan trọng nhất
của cả refactor: **model đề xuất, code phán quyết.** File này chỉ dựng ngữ cảnh,
gọi model, và trace. Việc "route này có chạy được trên tài liệu thật không" nằm
hẳn ở `intent.resolve_route()` — thuần Python, test bằng dữ liệu bịa, không tốn
lời gọi nào.

KHÔNG dùng function-calling của OpenAI, dù đây đúng là chỗ dành cho nó. Lý do:
với structured output thì mọi route là một JSON đọc được, đếm được trong
`eval/traces/`, và một route sai trở thành một case đo được cho golden set. Đổi
sang function-calling là mất chính tính chất đó, mà không thêm khả năng gì —
người dùng vẫn chỉ có ba việc làm được.
"""

from __future__ import annotations

from agent_core import intent as intent_lib
from agent_core import outline as outline_lib
from agent_core import scope as scope_lib
from agent_core.intent import Plan, UIContext
from agent_core.log import trace
from agent_core.models import Document
from agent_core.schemas import ROUTE_SCHEMA

PROMPT_ID = "route"
_HISTORY_TURNS = 6  # đủ để hiểu "phần đó" trỏ về đâu, chưa đủ để chủ đề cũ át chủ đề mới
_TURN_CHARS = 300


def route(doc: Document, message: str, ui: UIContext,
          history: list[dict] | None = None) -> Plan:
    """Trả `Plan` đã được code kiểm. Không bao giờ trả về một phạm vi không tồn tại.

    Lỗi tầng LLM (thiếu key, mất mạng) được để nguyên cho `app/` bắt và hiển thị
    `user_message`, giống hệt cách ba panel cũ vẫn làm — router không tự bịa ra
    một câu trả lời khi không gọi được model.
    """
    import providers  # import muộn: `import tools.router` phải rẻ, kể cả khi chưa có key

    result = providers.complete_json(
        PROMPT_ID,
        _variables(doc, message, ui, history),
        ROUTE_SCHEMA,
        "route",
        # Phân loại có enum sẵn + cây chương/mục đã đưa vào prompt: đây là việc
        # rẻ, và mọi route sai đều bị `intent.py` chặn thành một câu hỏi lại nên
        # thiệt hại có trần. Muốn chắc hơn thì trỏ OPENAI_MODEL_FAST sang model to.
        tier="fast",
        temperature=0.0,  # cùng một câu phải ra cùng một route, nếu không thì eval vô nghĩa
    )

    raw_route = intent_lib.route_from_dict(result.data)
    plan = intent_lib.resolve_route(doc, raw_route, ui)

    # Một dòng cho mỗi quyết định điều phối: đây là chỗ sai mới mà kiến trúc này
    # mang lại, nên nó phải đếm được chứ không chỉ chạy được.
    trace(
        "route",
        message=message,
        intent=raw_route.intent,
        proposed_scope=raw_route.scope,
        proposed_target=raw_route.target,
        # `decision` chứ không `kind`: `trace()` đã dùng tên `kind` cho tham số
        # vị trí đầu tiên của nó.
        decision=plan.kind,
        tool=plan.tool,
        scope=plan.scope,
        target_id=plan.target_id,
        n_items=plan.n_items,
        rationale=raw_route.rationale,
    )
    return plan


def _variables(doc: Document, message: str, ui: UIContext,
               history: list[dict] | None) -> dict[str, str]:
    return {
        "document_outline": outline_lib.outline_digest(doc.chapters)
                            or "(tài liệu này không tách được chương/mục — "
                               "chỉ chọn được theo trang, khoảng trang, hoặc toàn bộ)",
        "total_pages": str(len(doc.pages)),
        "current_page": str(ui.page_no),
        "active_quiz": f"bộ {ui.quiz_items} câu đang mở" if ui.quiz_items else "(chưa có)",
        "last_scope": _last_scope_label(doc, ui),
        "history": _format_history(history),
        "message": message,
    }


def _last_scope_label(doc: Document, ui: UIContext) -> str:
    """Nhãn phạm vi lượt trước — thứ duy nhất giải được "tạo quiz từ phần đó"."""
    if not ui.last_scope:
        return "(chưa có)"
    scope, target_id = ui.last_scope
    return f"{scope_lib.scope_label(doc, scope, target_id)} (scope={scope}, target={target_id or '-'})"


def _format_history(history: list[dict] | None) -> str:
    if not history:
        return "(chưa có)"
    recent = [t for t in history if t.get("role") in ("user", "assistant")][-_HISTORY_TURNS:]
    return "\n".join(
        f"{'Người dùng' if turn['role'] == 'user' else 'Trợ lý'}: "
        f"{str(turn.get('content', ''))[:_TURN_CHARS]}"
        for turn in recent
    ) or "(chưa có)"
