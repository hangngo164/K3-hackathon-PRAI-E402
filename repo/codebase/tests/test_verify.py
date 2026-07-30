"""Verifier là lớp canh nguồn sự thật — nó hỏng thì mọi thứ khác vô nghĩa.

Mỗi test dưới đây tương ứng một cách mà output của model từng lọt qua khi chưa
có luật: quote bịa, neo trỏ ra ngoài phạm vi, câu hỏi lộ đáp án, câu hỏi về hình
thức trang giấy.
"""

import pytest

from agent_core import verify
from agent_core.models import Anchor, ScopeContext


@pytest.fixture
def ctx() -> ScopeContext:
    return ScopeContext(
        scope="page",
        target_id="2",
        unit_ids=["p02", "p02-b01", "p02-b02"],
        text="Attention tính trọng số giữa các token. Công thức dùng Query, Key và Value.",
        est_tokens=30,
        strategy="direct",
    )


# --- so khớp trích dẫn ---

def test_quote_matches_exactly():
    assert verify.verify_quote_in_text("sample slide text",
                                       "This is a sample slide text with content.")


def test_quote_matches_ignores_whitespace():
    assert verify.verify_quote_in_text("sample    slide text", "This  is a sample slide text.")


def test_quote_matches_tolerates_punctuation_drift(ctx):
    """Model rất hay 'sửa hộ' dấu câu — sửa dấu phẩy không phải là bịa."""
    assert verify.quote_matches("Công thức dùng Query Key và Value", ctx.text)


def test_invented_quote_is_rejected(ctx):
    assert not verify.quote_matches("Transformer dùng mạng hồi quy hai chiều", ctx.text)


# --- neo nguồn ---

def test_anchor_outside_scope_is_rejected(ctx):
    """Neo sang trang ngoài phạm vi là cách tóm tắt 'trang 2' lặng lẽ nói về trang 9."""
    anchor = Anchor(page_no=9, block_ids=[], quote="Attention tính trọng số")
    assert not verify.check_anchor(anchor, ctx).passed


def test_anchor_with_unknown_block_is_rejected(ctx):
    anchor = Anchor(page_no=2, block_ids=["p02-b99"], quote="Attention tính trọng số")
    assert not verify.check_anchor(anchor, ctx).passed


def test_valid_anchor_passes(ctx):
    anchor = Anchor(page_no=2, block_ids=["p02-b01"], quote="Attention tính trọng số")
    assert verify.check_anchor(anchor, ctx).passed


# --- luật chống câu hỏi rác ---

def _item(**overrides) -> dict:
    base = {
        "item_id": "q1",
        "type": "mcq",
        "stem": "Ma trận nào mang thông tin được lấy ra?",
        "options": ["Value", "Query", "Key", "Softmax"],
        "answer_index": 0,
        "answer_text": "Value",
        "explanation": "Theo slide, Value mang thông tin được lấy ra.",
        "anchor": {"page_no": 2, "block_ids": ["p02-b02"],
                   "quote": "Công thức dùng Query, Key và Value"},
        "difficulty": "recall",
        "distractor_rationale": ["Query là token đang xét", "Key để so khớp", "Softmax là hàm"],
    }
    base.update(overrides)
    return base


def test_good_item_passes(ctx):
    assert verify.check_quiz_item(_item(), ctx).passed


def test_stem_leaking_answer_is_rejected(ctx):
    result = verify.check_quiz_item(
        _item(stem="Vì sao Value mang thông tin được lấy ra là đáp án đúng?",
              answer_text="Value mang thông tin được lấy ra"),
        ctx,
    )
    assert not result.passed


def test_option_length_imbalance_is_rejected(ctx):
    """Đáp án dài gấp bội là trò đoán mẹo, không phải kiểm tra kiến thức."""
    result = verify.check_quiz_item(
        _item(options=[
            "Value, tức ma trận mang toàn bộ thông tin sẽ được lấy ra sau khi tính trọng số",
            "Query", "Key", "Softmax",
        ]),
        ctx,
    )
    assert not result.passed


def test_question_about_document_shape_is_rejected(ctx):
    result = verify.check_quiz_item(
        _item(stem="Trang này có bao nhiêu gạch đầu dòng?"), ctx
    )
    assert not result.passed


def test_all_of_the_above_is_rejected(ctx):
    result = verify.check_quiz_item(
        _item(options=["Value", "Query", "Key", "Tất cả các đáp án trên"]), ctx
    )
    assert not result.passed


def test_wrong_option_count_is_rejected(ctx):
    assert not verify.check_quiz_item(_item(options=["Value", "Query"]), ctx).passed


def test_short_answer_shape(ctx):
    item = _item(type="short_answer", options=[], answer_index=-1, distractor_rationale=[])
    assert verify.check_quiz_item(item, ctx).passed


# --- số liệu: cảnh báo, không loại ---

def test_unknown_number_warns_but_passes():
    result = verify.check_numbers("Mô hình có 768 chiều", "Bản gốc dùng 512 chiều")
    assert result.passed
    assert result.warnings


# --- trích dẫn của chat ---

def test_citation_outside_retrieved_chunks_is_rejected():
    anchor = Anchor(page_no=7, block_ids=[], quote="Query, Key và Value")
    result = verify.check_citation(anchor, ["p02", "p02-b02"], "Công thức dùng Query, Key và Value")
    assert not result.passed
