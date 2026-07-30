"""Ngữ cảnh gửi cho router — "tạo quiz từ phần đó" chỉ giải được nếu nó đầy đủ.

`test_intent.py` kiểm phần phán quyết SAU khi model trả lời. File này kiểm phần
TRƯỚC đó: những gì code đưa vào prompt. Model không đoán được "phần đó" nếu
phạm vi lượt trước không có trong prompt, và không phân biệt được "câu 5" với
một câu hỏi thường nếu số câu quiz đang mở không có trong prompt.

Không lời gọi AI nào: `_variables()` là hàm thuần.
"""

from agent_core.intent import UIContext
from tools import router


def test_every_variable_the_prompt_needs_is_supplied(doc):
    """Biến thiếu ⇒ `prompting.render` thay bằng chuỗi rỗng, và model mất ngữ cảnh trong im lặng."""
    from agent_core import prompting

    variables = router._variables(doc, "tóm tắt trang này", UIContext(), None)
    template = prompting.load(router.PROMPT_ID).user_template
    assert prompting.missing_variables(template, variables) == []


def test_previous_scope_reaches_the_prompt_readably(doc):
    """"Phần đó" cần cả nhãn người đọc được lẫn scope/target máy dùng lại được."""
    ui = UIContext(page_no=2, last_scope=("chapter", "ch01"))
    label = router._variables(doc, "tạo quiz từ phần đó", ui, None)["last_scope"]
    assert "Self-Attention" in label
    assert "scope=chapter" in label and "target=ch01" in label


def test_no_previous_scope_says_so_instead_of_going_blank(doc):
    assert router._variables(doc, "tóm tắt", UIContext(), None)["last_scope"] == "(chưa có)"


def test_open_quiz_size_reaches_the_prompt(doc):
    """Không có số câu thì model không biết "câu 5" có tồn tại hay không."""
    variables = router._variables(doc, "tại sao câu 5 sai", UIContext(quiz_items=5), None)
    assert "5" in variables["active_quiz"]


def test_no_quiz_open_is_stated(doc):
    assert router._variables(doc, "câu 5 sai à", UIContext(), None)["active_quiz"] == "(chưa có)"


def test_chapter_tree_carries_unit_ids_so_the_model_can_copy_them(doc):
    outline = router._variables(doc, "tóm tắt chương 2", UIContext(), None)["document_outline"]
    assert "ch01" in outline and "ch01-s02" in outline and "ch02" in outline
    assert "Positional Encoding" in outline


def test_flat_document_says_it_has_no_chapters(doc):
    import dataclasses

    flat = dataclasses.replace(doc, chapters=[])
    outline = router._variables(flat, "tóm tắt chương 2", UIContext(), None)["document_outline"]
    assert "không tách được chương/mục" in outline


def test_history_is_trimmed_to_the_recent_turns(doc):
    """Nối cả hội thoại thì chủ đề cũ át chủ đề mới — và tiền token tăng mỗi lượt."""
    history = [{"role": "user", "content": f"câu {n}"} for n in range(20)]
    lines = router._variables(doc, "còn cái kia?", UIContext(), history)["history"].splitlines()
    assert len(lines) == router._HISTORY_TURNS
    assert "câu 19" in lines[-1]


def test_empty_history_is_stated(doc):
    assert router._variables(doc, "xin chào", UIContext(), [])["history"] == "(chưa có)"


def test_current_page_comes_from_the_ui_not_the_model(doc):
    variables = router._variables(doc, "tóm tắt trang này", UIContext(page_no=3), None)
    assert variables["current_page"] == "3"
    assert variables["total_pages"] == str(len(doc.pages))
