"""Scope là cửa duy nhất lấy văn bản — rò một trang ngoài phạm vi là hỏng cả chuỗi.

Nếu `unit_ids` chứa trang không thuộc phạm vi thì `verify` sẽ chấp nhận một neo
sai, và "tóm tắt chương 1" lặng lẽ trích dẫn chương 2.
"""

import pytest

from agent_core import scope as scope_lib
from agent_core.errors import NoGroundedSource


def test_block_ids_stay_in_unit_ids_so_anchors_can_be_checked(doc):
    """Bỏ bôi đen KHÔNG được làm mất id khối: verify dùng chúng để bắt neo trỏ ra ngoài."""
    ctx = scope_lib.resolve(doc, "page", "2")
    assert "p02-b02" in ctx.unit_ids
    assert "(p02-b02)" in ctx.annotated_text  # model vẫn thấy id để đặt anchor


def test_page_scope_only_contains_that_page(doc):
    ctx = scope_lib.resolve(doc, "page", "2")
    assert ctx.unit_ids == ["p02", "p02-b01", "p02-b02", "p02-b03"]
    assert "Positional Encoding" not in ctx.text


def test_chapter_scope_covers_exactly_its_pages(doc):
    ctx = scope_lib.resolve(doc, "chapter", "ch01")
    pages = {u for u in ctx.unit_ids if "-b" not in u}
    assert pages == {"p01", "p02", "p03"}
    assert "p04" not in ctx.unit_ids  # chương 2 không được lọt vào


def test_section_scope_narrower_than_its_chapter(doc):
    section = scope_lib.resolve(doc, "section", "ch01-s02")
    chapter = scope_lib.resolve(doc, "chapter", "ch01")
    assert set(section.unit_ids) < set(chapter.unit_ids)


def test_page_range_scope_covers_exactly_that_span(doc):
    ctx = scope_lib.resolve(doc, "pages", "2-3")
    assert {u for u in ctx.unit_ids if "-b" not in u} == {"p02", "p03"}
    assert scope_lib.scope_label(doc, "pages", "2-3") == "Trang 2-3"


def test_page_range_skips_image_only_pages_inside_it(doc):
    """Trang toàn hình nằm giữa khoảng không được vào phạm vi neo."""
    ctx = scope_lib.resolve(doc, "pages", "4-5")
    assert "p05" not in ctx.unit_ids


def test_page_range_is_parsed_one_way_everywhere(doc):
    assert scope_lib.parse_page_range("5-12") == (5, 12)
    assert scope_lib.parse_page_range("12-5") == (5, 12)   # đảo lại, không từ chối
    assert scope_lib.parse_page_range("7") == (7, 7)
    assert scope_lib.parse_page_range("phần đầu") is None


def test_document_scope_skips_image_only_pages(doc):
    """Trang toàn hình không có gì để trích, nên không được vào phạm vi neo."""
    ctx = scope_lib.resolve(doc, "document")
    assert "p05" not in ctx.unit_ids


def test_image_only_page_abstains(doc):
    with pytest.raises(NoGroundedSource):
        scope_lib.resolve(doc, "page", "5")


def test_map_reduce_plan_skips_image_only_pages(doc):
    assert 5 not in scope_lib.plan_map_reduce(doc, "document")


def test_estimate_job_counts_readable_pages_only(doc):
    estimate = scope_lib.estimate_job(doc, "document")
    assert estimate["pages"] == 5
    assert estimate["readable_pages"] == 4


def test_page_list_label_lists_pages_in_scope(doc):
    ctx = scope_lib.resolve(doc, "chapter", "ch01")
    assert scope_lib.page_list_label(ctx) == "1, 2, 3"
