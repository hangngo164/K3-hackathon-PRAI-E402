"""Khai báo các tool cho UI và `eval/run.py` dùng chung.

Vì sao cần registry khi chỉ có ba tool: `app/` và `eval/run.py` là hai người
gọi độc lập. Không có bảng khai báo thì mỗi bên tự biết "tool nào nhận scope
nào, số câu bao nhiêu là hợp lệ", và hai bên trôi khỏi nhau — lúc đó bảng đo
của eval không còn nói về thứ người dùng thật sự bấm.

Đây KHÔNG phải tool-calling: model không đọc bảng này và không chọn tool. Người
dùng chọn trên UI, code tra bảng rồi gọi. Model chỉ điền JSON đúng schema.
Giữ như vậy thì mọi đường đi đều liệt kê được và đo được.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

ALL_SCOPES = ("page", "pages", "section", "chapter", "document")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str            # nhãn hiện trên UI
    description: str      # một câu, dùng cho tooltip và cho README
    scopes: tuple[str, ...]  # phạm vi tool này nhận; () = không dùng scope
    prompt_id: str
    automation: str       # 'automate' | 'augment' — quyết định UI cảnh báo tới đâu
    run: Callable[..., dict]


# Ba hàm bọc dưới đây import muộn có chủ đích: `import tools.registry` phải
# đọc được bảng khai báo mà KHÔNG kéo theo `providers` và SDK openai —
# `check_env.py` cần liệt kê tool khi máy chưa cài đủ hoặc chưa có API key.

def _summarize(**kwargs: Any) -> dict:
    from . import summarize as module
    return module.summarize(**kwargs)


def _quiz(**kwargs: Any) -> dict:
    from . import quiz as module
    return module.generate(**kwargs)


def _ask(**kwargs: Any) -> dict:
    from . import ask as module
    return module.ask(**kwargs)


REGISTRY: dict[str, ToolSpec] = {
    "summarize": ToolSpec(
        name="summarize",
        title="Tóm tắt",
        description="Tóm tắt một phạm vi: một trang, một khoảng trang, một mục, "
                    "một chương, hoặc toàn bộ tài liệu.",
        scopes=ALL_SCOPES,
        prompt_id="summarize",
        # Bullet nào cũng có nút "xem chỗ này" nên người dùng kiểm được trong
        # một cú bấm => sai rẻ => không cần người duyệt trước.
        automation="automate",
        run=_summarize,
    ),
    "quiz": ToolSpec(
        name="quiz",
        title="Tạo quiz",
        description="Sinh câu hỏi ôn tập có trích dẫn trang. Quiz toàn tài liệu "
                    "được ghép từ nhiều lượt sinh theo từng phần.",
        scopes=ALL_SCOPES,
        prompt_id="quiz",
        # Đáp án sai dạy người học kiến thức sai ngay trước kỳ đánh giá => sai đắt.
        automation="augment",
        run=_quiz,
    ),
    "ask": ToolSpec(
        name="ask",
        title="Hỏi đáp",
        description="Hỏi tự do về nội dung tài liệu; câu trả lời luôn kèm trích "
                    "dẫn trang, không tìm thấy thì nói không tìm thấy.",
        # Khác summarize/quiz: phạm vi là TUỲ CHỌN. Không truyền thì tự tìm trên
        # cả tài liệu bằng agent_core/retrieve.py; truyền thì chỉ thu hẹp vùng tìm.
        scopes=ALL_SCOPES,
        prompt_id="ask",
        automation="augment",
        run=_ask,
    ),
}


def names() -> list[str]:
    return list(REGISTRY)


def get(name: str) -> ToolSpec:
    if name not in REGISTRY:
        raise KeyError(f"Không có tool '{name}'. Hiện có: {', '.join(REGISTRY)}")
    return REGISTRY[name]


def run(name: str, **kwargs: Any) -> dict:
    """Cửa vào duy nhất cho `app/` và `eval/run.py`."""
    return get(name).run(**kwargs)


def supports(name: str, scope: str) -> bool:
    spec = get(name)
    return not spec.scopes or scope in spec.scopes
