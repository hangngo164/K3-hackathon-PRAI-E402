"""Prompt là file có version — nạp hỏng thì chỉ lộ ra lúc bấm nút giữa buổi demo.

Test này chạy trên prompt THẬT trong `prompts/`, không phải file bịa: mục đích
là bắt lỗi gõ tên biến và mục thiếu ngay khi ai đó sửa prompt.
"""

import pytest

from agent_core import prompting
from agent_core.schemas import ANSWER_SCHEMA, QUIZ_SCHEMA, ROUTE_SCHEMA, SUMMARY_SCHEMA

# Biến mà code thật sự truyền vào, theo từng prompt
_EXPECTED_VARIABLES = {
    "summarize": {"source_text", "context_text", "scope_label",
                  "n_bullets_min", "n_bullets_max", "page_list"},
    "quiz": {"source_text", "scope_label", "n_items", "difficulty_mix",
             "page_list", "avoid_facts", "repair_feedback"},
    "ask": {"source_text", "history", "question"},
    "outline": {"page_titles", "total_pages"},
    "route": {"document_outline", "total_pages", "current_page",
              "active_quiz", "last_scope", "history", "message"},
}


@pytest.mark.parametrize("prompt_id", sorted(_EXPECTED_VARIABLES))
def test_prompt_loads_with_both_sections(prompt_id):
    prompt = prompting.load(prompt_id)
    assert prompt.system.strip(), f"{prompt_id} thiếu mục '# SYSTEM'"
    assert prompt.user_template.strip(), f"{prompt_id} thiếu mục '# USER'"
    assert prompt.version.startswith("v")


@pytest.mark.parametrize("prompt_id,variables", sorted(_EXPECTED_VARIABLES.items()))
def test_prompt_uses_exactly_the_variables_code_passes(prompt_id, variables):
    """Biến thừa trong prompt = chỗ luôn rỗng; biến thiếu = tham số bị bỏ qua."""
    prompt = prompting.load(prompt_id)
    missing = prompting.missing_variables(prompt.user_template, dict.fromkeys(variables, ""))
    assert missing == [], f"{prompt_id} dùng biến code không truyền: {missing}"


def test_html_comments_never_reach_the_model():
    """Comment trong file prompt là ghi chú cho người đọc repo, không phải chỉ dẫn."""
    prompt = prompting.load("summarize")
    assert "<!--" not in prompt.system
    assert "<!--" not in prompt.user_template


def test_render_leaves_json_braces_alone():
    """Prompt chứa ví dụ JSON — dùng str.format ở đây sẽ nổ hoặc nuốt dấu ngoặc."""
    rendered = prompting.render('Ví dụ: {"a": 1} và {{ten}}', {"ten": "giá trị"})
    assert rendered == 'Ví dụ: {"a": 1} và giá trị'


def test_missing_variable_becomes_empty_string():
    """`repair_feedback` để trống ở lượt sinh đầu là hợp lệ, không được ném lỗi."""
    assert prompting.render("A{{khong_co}}B", {}) == "AB"


@pytest.mark.parametrize("schema", [SUMMARY_SCHEMA, QUIZ_SCHEMA, ANSWER_SCHEMA, ROUTE_SCHEMA])
def test_schemas_satisfy_openai_strict_mode(schema):
    """`strict: true` bắt buộc: mọi property phải required, cấm additionalProperties.

    Vi phạm là API trả 400 — không phải model trả sai, nên test bắt được sớm.
    """
    _assert_strict(schema)


def _assert_strict(node) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, node.get("properties", {}).keys()
            assert set(node.get("required", [])) == set(node.get("properties", {}))
        for value in node.values():
            _assert_strict(value)
    elif isinstance(node, list):
        for value in node:
            _assert_strict(value)
