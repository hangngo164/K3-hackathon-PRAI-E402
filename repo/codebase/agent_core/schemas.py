"""Hợp đồng output — JSON schema cho structured output.

Đây là chỗ DUY NHẤT định nghĩa "output đúng là gì": `providers/`, `tools/`,
`agent_core/verify.py` và `eval/run.py` đều đọc từ đây, nên đổi hợp đồng là
đổi ở một chỗ.

File lá: không chứa prompt, không import module nào khác trong `agent_core/`.

Ràng buộc của OpenAI `strict: true` — vi phạm là API trả 400, không phải model
trả sai:
  · mọi object phải có `additionalProperties: false`
  · MỌI property phải nằm trong `required` (không có field tuỳ chọn)
  · không dùng minLength/maxLength/minItems/pattern/minimum...

Hệ quả của luật thứ hai: field "có thể trống" được khai bằng giá trị rỗng quy
ước (`options: []`, `answer_index: -1`, `refusal_reason: ""`) chứ không phải
bằng cách bỏ field đi. Hệ quả của luật thứ ba: mọi giới hạn số lượng/độ dài
phải kiểm bằng code ở `verify.py`, không nhờ được schema.
"""

from __future__ import annotations

from typing import Any

Scope = str  # "document" | "chapter" | "section" | "pages" | "page"


def _obj(properties: dict[str, Any]) -> dict[str, Any]:
    """Object strict-mode: mọi property đều required, cấm field lạ."""
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


# --- Neo nguồn: dùng lại trong cả ba hợp đồng dưới ---
# Không có neo thì không kiểm được bằng code, và cả hệ thống mất tính "đo được".
ANCHOR_SCHEMA: dict = _obj({
    "page_no": {
        "type": "integer",
        "description": "Số trang 1-based, phải nằm trong phạm vi đã cho.",
    },
    "block_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Id khối văn bản dạng 'p06-b03' lấy từ nguồn. Không biết thì để [].",
    },
    "quote": {
        "type": "string",
        "description": "Trích NGUYÊN VĂN <=200 ký tự từ nguồn. Không diễn đạt lại, không dịch.",
    },
})

BULLET_SCHEMA: dict = _obj({
    "text": {"type": "string", "description": "Một ý, một câu, viết bằng tiếng Việt."},
    "anchor": ANCHOR_SCHEMA,
})

KEY_TERM_SCHEMA: dict = _obj({
    "term": {"type": "string", "description": "Giữ NGUYÊN dạng viết trên slide, kể cả tiếng Anh."},
    "meaning": {"type": "string", "description": "Giải thích ngắn bằng tiếng Việt, chỉ từ nguồn."},
    "page_no": {"type": "integer", "description": "Trang định nghĩa thuật ngữ này."},
})

SUMMARY_SCHEMA: dict = _obj({
    "scope_label": {"type": "string", "description": "Nhãn phạm vi, ví dụ 'Trang 6' hay 'Chương 2'."},
    "tldr": {"type": "string", "description": "Đúng MỘT câu."},
    "bullets": {"type": "array", "items": BULLET_SCHEMA},
    "key_terms": {"type": "array", "items": KEY_TERM_SCHEMA},
    "not_covered": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Phần KHÔNG đọc được từ nguồn (sơ đồ, công thức dạng ảnh). Không im lặng bỏ qua.",
    },
    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
})

QUIZ_ITEM_SCHEMA: dict = _obj({
    "item_id": {"type": "string", "description": "Duy nhất trong một bộ, ví dụ 'q1'."},
    "type": {"type": "string", "enum": ["mcq", "true_false", "short_answer"]},
    "stem": {"type": "string", "description": "Câu hỏi. KHÔNG chứa nguyên văn đáp án."},
    "options": {
        "type": "array",
        "items": {"type": "string"},
        "description": "mcq: 4 phương án · true_false: ['Đúng','Sai'] · short_answer: [].",
    },
    "answer_index": {
        "type": "integer",
        "description": "Vị trí 0-based của đáp án đúng trong options. short_answer thì -1.",
    },
    "answer_text": {"type": "string", "description": "Đáp án dạng chữ, luôn phải điền."},
    "explanation": {"type": "string", "description": "Vì sao đúng — chỉ suy từ quote trong anchor."},
    "anchor": ANCHOR_SCHEMA,
    "difficulty": {"type": "string", "enum": ["recall", "understand", "apply"]},
    "distractor_rationale": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Mỗi phương án SAI một dòng: sai ở đâu theo nguồn. short_answer thì [].",
    },
})

QUIZ_SCHEMA: dict = _obj({
    "items": {"type": "array", "items": QUIZ_ITEM_SCHEMA},
    "notes": {
        "type": "string",
        "description": "Nguồn mỏng nên sinh ít câu hơn yêu cầu thì nói ở đây. Không thì ''.",
    },
})

# --- Chat hỏi đáp trên tài liệu ---
# Khác summary/quiz ở một điểm: câu hỏi do người dùng gõ tự do nên model PHẢI
# được phép trả lời "không có trong tài liệu". `answerable=false` là đường thoát
# hợp lệ, không phải thất bại — thiếu nó thì model buộc phải bịa.
ANSWER_SCHEMA: dict = _obj({
    "answerable": {
        "type": "boolean",
        "description": "false khi các đoạn đã cho không đủ căn cứ trả lời.",
    },
    "answer": {"type": "string", "description": "Trả lời bằng tiếng Việt. answerable=false thì ''."},
    "citations": {
        "type": "array",
        "items": ANCHOR_SCHEMA,
        "description": "Mỗi ý trong answer phải có ít nhất một neo. answerable=false thì [].",
    },
    "refusal_reason": {
        "type": "string",
        "enum": ["", "not_in_document", "out_of_scope", "too_vague"],
        "description": "not_in_document: tài liệu không nói · out_of_scope: đòi việc ngoài "
                       "phạm vi ôn slide · too_vague: câu hỏi chưa đủ rõ để tìm.",
    },
    "followup": {
        "type": "string",
        "description": "Việc làm được tiếp theo, gợi ý cho người dùng. Không có thì ''.",
    },
    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
})

OUTLINE_SCHEMA: dict = _obj({
    "chapters": {
        "type": "array",
        "items": _obj({
            "title": {"type": "string", "description": "Lấy từ tiêu đề trang CÓ THẬT, không tự đặt."},
            "start_page": {"type": "integer"},
            "end_page": {"type": "integer"},
            "sections": {
                "type": "array",
                "items": _obj({
                    "title": {"type": "string"},
                    "start_page": {"type": "integer"},
                    "end_page": {"type": "integer"},
                }),
            },
        }),
        "description": "Không chắc tài liệu có cấu trúc thì trả [] — hệ thống tự tụt về 'flat'.",
    },
})


# --- Điều phối: ý người dùng gõ ra → tool nào, phạm vi nào ---
# Đây là chỗ DUY NHẤT model được chọn hành động, và nó chọn bằng cách điền JSON
# chứ không bằng function-calling. Model chỉ ĐỀ XUẤT; `agent_core/intent.py`
# đối chiếu route vào tài liệu thật (chương này có tồn tại? trang này có trong
# tài liệu?) rồi mới dispatch. Nhờ vậy một route sai là một dòng trace đọc được
# và đếm được, không phải một hộp đen — và `verify.py` phía sau vẫn nhận đúng
# một `ScopeContext` xác định như trước.
ROUTE_SCHEMA: dict = _obj({
    "intent": {
        "type": "string",
        "enum": ["summarize", "quiz", "ask", "explain_quiz", "clarify"],
        "description": "clarify khi câu vào có nhiều cách hiểu hoặc thiếu thông tin để chạy. "
                       "explain_quiz khi người dùng hỏi về một câu trong bộ quiz đang mở.",
    },
    "scope": {
        "type": "string",
        "enum": ["", "page", "pages", "section", "chapter", "document"],
        "description": "Phạm vi cho summarize/quiz, và cho ask khi câu hỏi tự nêu phạm vi. "
                       "Câu hỏi không gắn phần nào thì ''.",
    },
    "target": {
        "type": "string",
        "description": "page: số trang người dùng nói, dạng chữ số ('6') — bỏ trống CHỈ KHI họ "
                       "không nói số nào · pages: khoảng dạng '5-12' · section/chapter: unit_id "
                       "LẤY TỪ cây chương/mục đã cho ('ch02', 'ch02-s03'), không tự đặt id mới "
                       "· document: ''.",
    },
    "n_items": {
        "type": "integer",
        "description": "quiz: số câu người dùng xin. Người dùng KHÔNG nói số thì 0 để code tự chọn.",
    },
    "question": {
        "type": "string",
        "description": "ask: câu hỏi đã viết lại đủ nghĩa một mình (thay 'cái đó' bằng tên thật "
                       "lấy từ hội thoại). clarify: đúng MỘT câu hỏi lại. Khác thì ''.",
    },
    "options": {
        "type": "array",
        "items": {"type": "string"},
        "description": "clarify: 2-3 lựa chọn ngắn để người dùng bấm thay vì gõ lại. Khác thì [].",
    },
    "item_no": {
        "type": "integer",
        "description": "explain_quiz: số thứ tự câu trong bộ quiz đang mở, 1-based. Khác thì 0.",
    },
    "rationale": {
        "type": "string",
        "description": "Một câu vì sao chọn intent và phạm vi này. Đi vào trace, không hiện cho người dùng.",
    },
})


# --- Ngưỡng do CODE quyết, không để model tự chọn ---

_BULLETS = {
    "page": (3, 5),
    "pages": (4, 6),   # khoảng trang tuỳ ý: rộng hơn một trang, hẹp hơn một mục
    "section": (5, 7),
    "chapter": (6, 9),
    "document": (8, 12),
}

_DIFFICULTY = {
    "page": {"recall": 0.5, "understand": 0.4, "apply": 0.1},
    "pages": {"recall": 0.4, "understand": 0.4, "apply": 0.2},
    "section": {"recall": 0.4, "understand": 0.4, "apply": 0.2},
    "chapter": {"recall": 0.4, "understand": 0.4, "apply": 0.2},
    "document": {"recall": 0.3, "understand": 0.4, "apply": 0.3},
}


def bullets_range(scope: Scope) -> tuple[int, int]:
    """Số bullet cho phép theo scope.

    Độ dài do code quyết vì đây là quyết định sản phẩm ("tóm tắt phải ngắn hơn
    bản gốc"), không phải việc model đoán ý người dùng.
    """
    return _BULLETS.get(scope, (3, 5))


def difficulty_mix(scope: Scope) -> dict[str, float]:
    """Cơ cấu độ khó theo scope. Phạm vi càng rộng càng nghiêng về apply."""
    return _DIFFICULTY.get(scope, _DIFFICULTY["page"])


def difficulty_label(scope: Scope) -> str:
    """Chuỗi đưa vào prompt, ví dụ 'recall 60% · understand 40%'."""
    return " · ".join(
        f"{name} {int(round(ratio * 100))}%"
        for name, ratio in difficulty_mix(scope).items()
        if ratio > 0
    )
