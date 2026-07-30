"""Route của model là ĐỀ XUẤT — file này kiểm phần code phán quyết nó.

Đây là chỗ sai mới mà refactor sang một-cửa-sổ-chat mang lại: trước đây người
dùng bấm phạm vi nên phạm vi luôn có thật. Giờ model đề xuất phạm vi, nên
"chương không tồn tại" và "trang ngoài tài liệu" trở thành đầu vào bình thường,
và cả hai phải quy về hỏi lại — không được nổ, không được chạy trên phạm vi sai.

Không lời gọi AI nào trong file này: `resolve_route` là logic thuần.
"""

import dataclasses

import pytest

from agent_core import intent
from agent_core.intent import Route, UIContext

_UI = UIContext(page_no=2, quiz_items=0)


def _route(**kwargs) -> Route:
    return Route(**kwargs)


# --- Phạm vi phải có thật trong tài liệu ---

def test_page_out_of_range_asks_back_with_the_real_count(doc):
    """Deck 5 trang, model đề xuất trang 60: phải hỏi lại và nói đúng số trang."""
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="page", target="60"), _UI)
    assert plan.kind == "clarify"
    assert "5 trang" in plan.question
    assert plan.options


def test_valid_page_becomes_a_tool_call(doc):
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="page", target="2"), _UI)
    assert (plan.kind, plan.tool, plan.scope, plan.target_id) == ("tool", "summarize", "page", "2")


def test_empty_target_means_the_page_being_viewed(doc):
    """"Tóm tắt trang này" — trang phải lấy từ UI, không để model nhớ hộ."""
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="page"), _UI)
    assert plan.target_id == "2"


def test_page_number_inside_a_phrase_is_parsed(doc):
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="page", target="trang 3"), _UI)
    assert plan.target_id == "3"


def test_unparseable_page_asks_back(doc):
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="page", target="cuối"), _UI)
    assert plan.kind == "clarify"


def test_unknown_chapter_lists_the_chapters_that_exist(doc):
    """Hỏi lại phải kèm lựa chọn CÓ THẬT — nếu không thì người dùng đoán lần hai."""
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="chapter", target="ch99"), _UI)
    assert plan.kind == "clarify"
    assert plan.options == ["Self-Attention", "Positional Encoding"]


def test_known_chapter_passes_through(doc):
    plan = intent.resolve_route(doc, _route(intent="quiz", scope="chapter", target="ch01"), _UI)
    assert (plan.kind, plan.scope, plan.target_id) == ("tool", "chapter", "ch01")


def test_chapter_and_section_refused_when_document_is_flat(doc):
    """Tài liệu không tách được chương/mục: nói lý do, không dựng chương giả."""
    flat = dataclasses.replace(doc, chapters=[])
    plan = intent.resolve_route(flat, _route(intent="summarize", scope="chapter", target="ch01"), _UI)
    assert plan.kind == "clarify"
    assert "không tách được chương/mục" in plan.question


# --- Khớp theo TÊN mục, vì người dùng gõ "phần giới thiệu" chứ không gõ ch01-s01 ---

def test_title_without_diacritics_finds_the_chapter(doc):
    plan = intent.resolve_route(
        doc, _route(intent="summarize", scope="chapter", target="positional encoding"), _UI
    )
    assert (plan.scope, plan.target_id) == ("chapter", "ch02")


def test_partial_title_finds_the_section(doc):
    plan = intent.resolve_route(
        doc, _route(intent="summarize", scope="section", target="Query/Key/Value"), _UI
    )
    assert (plan.scope, plan.target_id) == ("section", "ch01-s02")


def test_title_matching_two_units_asks_instead_of_picking(doc):
    """Hai phần cùng khớp một cái tên là đúng lúc phải hỏi, không được chọn hộ."""
    chapter = doc.chapters[0]
    twin = dataclasses.replace(
        chapter.sections[0], unit_id="ch01-s01", title="Positional Encoding"
    )
    ambiguous = dataclasses.replace(
        doc,
        chapters=[dataclasses.replace(chapter, sections=[twin] + list(chapter.sections[1:])),
                  doc.chapters[1]],
    )
    plan = intent.resolve_route(
        ambiguous, _route(intent="summarize", scope="chapter", target="Positional Encoding"), _UI
    )
    assert plan.kind == "clarify"
    assert len(plan.options) == 2


# --- Khoảng trang: "tóm tắt trang 2 đến 4" ---

def test_page_range_becomes_the_pages_scope(doc):
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="pages", target="2-4"), _UI)
    assert (plan.kind, plan.scope, plan.target_id) == ("tool", "pages", "2-4")


def test_reversed_range_is_read_the_only_way_it_can_mean(doc):
    """'4-2' không mơ hồ — đảo lại là số học, không phải đoán ý."""
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="pages", target="4-2"), _UI)
    assert plan.target_id == "2-4"


def test_single_number_range_collapses_to_one_page(doc):
    plan = intent.resolve_route(doc, _route(intent="quiz", scope="pages", target="3"), _UI)
    assert (plan.scope, plan.target_id) == ("page", "3")


def test_range_past_the_end_asks_with_the_clipped_range_ready(doc):
    """Cắt hộ vẫn là giả định — hỏi, nhưng để đồng ý chỉ mất một cú bấm."""
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="pages", target="2-90"), _UI)
    assert plan.kind == "clarify"
    assert "Trang 2 đến 5" in plan.options


def test_unparseable_range_asks_back(doc):
    plan = intent.resolve_route(
        doc, _route(intent="summarize", scope="pages", target="phần đầu"), _UI
    )
    assert plan.kind == "clarify"


# --- ask: phạm vi là tuỳ chọn ---

def test_ask_without_scope_searches_the_whole_document(doc):
    """"Attention là gì" không được bó về trang đang mở."""
    plan = intent.resolve_route(doc, _route(intent="ask", question="Attention là gì?"), _UI)
    assert (plan.tool, plan.scope, plan.target_id) == ("ask", "", None)


def test_ask_can_carry_a_scope_when_the_question_names_one(doc):
    plan = intent.resolve_route(
        doc, _route(intent="ask", scope="page", target="3", question="Trang 3 nói gì về Key?"), _UI
    )
    assert (plan.tool, plan.scope, plan.target_id) == ("ask", "page", "3")


def test_ask_with_a_bad_scope_asks_back(doc):
    plan = intent.resolve_route(
        doc, _route(intent="ask", scope="chapter", target="ch99", question="Chương 99 nói gì?"), _UI
    )
    assert plan.kind == "clarify"


# --- Phạm vi ngầm định: lấy chỗ người dùng đang đứng, không đoán ---

def test_missing_scope_falls_back_to_the_current_page(doc):
    plan = intent.resolve_route(doc, _route(intent="summarize"), _UI)
    assert (plan.scope, plan.target_id) == ("page", "2")


def test_selection_scope_is_no_longer_valid(doc):
    """Bôi đen đã bị bỏ: model lỡ đề xuất `selection` thì phải hỏi lại, không nổ."""
    plan = intent.resolve_route(doc, _route(intent="summarize", scope="selection"), _UI)
    assert plan.kind == "clarify"
    assert plan.options


def test_invalid_scope_name_asks_back(doc):
    plan = intent.resolve_route(doc, _route(intent="quiz", scope="paragraph"), _UI)
    assert plan.kind == "clarify"


# --- Số câu quiz: code quyết mặc định, người dùng nói số thì tôn trọng ---

def test_whole_document_quiz_defaults_into_the_10_20_band(doc):
    plan = intent.resolve_route(doc, _route(intent="quiz", scope="document"), _UI)
    assert 10 <= plan.n_items <= 20


def test_partial_quiz_defaults_into_the_3_7_band(doc):
    plan = intent.resolve_route(doc, _route(intent="quiz", scope="page", target="2"), _UI)
    assert 3 <= plan.n_items <= 7


def test_explicit_count_is_respected(doc):
    plan = intent.resolve_route(
        doc, _route(intent="quiz", scope="page", target="2", n_items=3), _UI
    )
    assert plan.n_items == 3


def test_absurd_count_is_capped(doc):
    plan = intent.resolve_route(
        doc, _route(intent="quiz", scope="document", n_items=500), _UI
    )
    assert plan.n_items == 20


def test_summarize_never_carries_an_item_count(doc):
    plan = intent.resolve_route(
        doc, _route(intent="summarize", scope="page", target="2", n_items=9), _UI
    )
    assert plan.n_items == 0


# --- "Tại sao câu số 5 sai?" — trả lời từ bộ quiz đang mở ---

def test_explain_needs_a_quiz_on_screen(doc):
    plan = intent.resolve_route(doc, _route(intent="explain_quiz", item_no=5), _UI)
    assert plan.kind == "clarify"
    assert "chưa có bộ quiz" in plan.question


def test_explain_rejects_an_item_number_out_of_range(doc):
    ui = dataclasses.replace(_UI, quiz_items=5)
    plan = intent.resolve_route(doc, _route(intent="explain_quiz", item_no=9), ui)
    assert plan.kind == "clarify"
    assert "5 câu" in plan.question


def test_explain_resolves_without_calling_a_tool(doc):
    """Câu quiz đã có explanation + quote đã verify — gọi model lần nữa là thêm chỗ bịa."""
    ui = dataclasses.replace(_UI, quiz_items=5)
    plan = intent.resolve_route(doc, _route(intent="explain_quiz", item_no=3), ui)
    assert (plan.kind, plan.item_no, plan.tool) == ("explain", 3, "")


# --- ask · clarify · rác ---

def test_ask_passes_the_rewritten_question(doc):
    plan = intent.resolve_route(
        doc, _route(intent="ask", question="Query khác Key chỗ nào?"), _UI
    )
    assert (plan.kind, plan.tool) == ("tool", "ask")
    assert plan.question == "Query khác Key chỗ nào?"


def test_ask_without_a_question_asks_back(doc):
    plan = intent.resolve_route(doc, _route(intent="ask"), _UI)
    assert plan.kind == "clarify"


def test_clarify_from_the_model_keeps_its_options(doc):
    plan = intent.resolve_route(
        doc, _route(intent="clarify", question="Trang 5 hay chương 5?",
                    options=["Trang 5", "Chương 5"]), _UI
    )
    assert (plan.kind, plan.options) == ("clarify", ["Trang 5", "Chương 5"])


def test_option_list_is_capped(doc):
    plan = intent.resolve_route(
        doc, _route(intent="clarify", question="?", options=[f"o{n}" for n in range(9)]), _UI
    )
    assert len(plan.options) <= 4


def test_unknown_intent_offers_the_three_things_it_can_do(doc):
    plan = intent.resolve_route(doc, _route(intent="translate_document"), _UI)
    assert plan.kind == "clarify"
    assert plan.options


# --- Parse JSON của model: méo cũng không được nổ ---

@pytest.mark.parametrize("raw", [
    {},
    {"intent": None, "scope": 5, "target": 6, "n_items": "nhiều", "options": "không phải list"},
    {"intent": "quiz", "n_items": None, "item_no": "3"},
])
def test_route_from_dict_survives_garbage(raw):
    route = intent.route_from_dict(raw)
    assert isinstance(route.n_items, int)
    assert isinstance(route.options, list)


def test_route_from_dict_reads_a_well_formed_payload():
    route = intent.route_from_dict({
        "intent": "quiz", "scope": "chapter", "target": "ch02", "n_items": 8,
        "question": "", "options": [], "item_no": 0, "rationale": "người dùng xin quiz chương 2",
    })
    assert (route.intent, route.scope, route.target, route.n_items) == ("quiz", "chapter", "ch02", 8)
