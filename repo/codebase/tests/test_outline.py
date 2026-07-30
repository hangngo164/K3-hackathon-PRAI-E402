"""Khoảng trang của chương/mục phải liền nhau, không chồng lấn, phủ hết tài liệu.

`_build_from_starts` chỉ tin `start_page` và tự tính `end_page`, nên tính chất
trên đúng theo cấu tạo — kể cả khi model ở bậc 3 trả khoảng trang bậy. Các test
dưới đây khoá đúng tính chất đó lại.
"""

from agent_core import outline


def _coverage(chapters, total_pages: int) -> list[int]:
    covered = []
    for chapter in chapters:
        first, last = chapter.page_range
        covered.extend(range(first, last + 1))
    return covered


def test_toc_builds_contiguous_chapters():
    toc = [[1, "Mở đầu", 1], [1, "Self-Attention", 2], [2, "Query/Key/Value", 3],
           [1, "Positional Encoding", 4]]
    chapters = outline.from_toc(toc, total_pages=6)
    assert [c.page_range for c in chapters] == [(1, 1), (2, 3), (4, 6)]
    assert _coverage(chapters, 6) == [1, 2, 3, 4, 5, 6]


def test_toc_ignored_when_no_level_one_entry():
    assert outline.from_toc([[2, "Chỉ có mục con", 1]], total_pages=4) is None


def test_llm_tier_repairs_overlapping_ranges():
    """Model trả khoảng chồng lấn (1-3 và 2-5) — code phải tự cắt lại, không tin."""
    def grouper(_titles, _total):
        return [
            {"title": "A", "start_page": 1, "end_page": 3, "sections": []},
            {"title": "B", "start_page": 2, "end_page": 5, "sections": []},
        ]

    chapters = outline.from_llm(_fake_pages(), grouper)
    assert [c.page_range for c in chapters] == [(1, 1), (2, 4)]


def test_llm_tier_returns_none_on_empty_result():
    assert outline.from_llm(_fake_pages(), lambda _t, _n: []) is None


def test_llm_tier_survives_a_crashing_grouper():
    """Dò chương/mục hỏng không được làm chết bước nạp file."""
    def boom(_titles, _total):
        raise RuntimeError("hết quota")

    assert outline.from_llm(_fake_pages(), boom) is None


def test_build_outline_falls_back_to_flat():
    """Không tách được thì trả rỗng + 'flat', KHÔNG dựng một chương giả."""
    chapters, source = outline.build_outline(_fake_pages(), toc=[], grouper=None)
    assert chapters == []
    assert source == "flat"


def test_unit_label_reads_like_a_breadcrumb(doc):
    assert outline.unit_label(doc.chapters, "ch01-s02").startswith("Self-Attention › ")


def _fake_pages():
    from agent_core.models import Block, Page

    def page(no: int) -> Page:
        block = Block(block_id=f"p{no:02d}-b01", page_no=no, order=1, text=f"Tiêu đề {no}",
                      bbox=(0.0, 0.0, 100.0, 20.0), font_size_max=20.0, is_title_like=True)
        return Page(page_no=no, blocks=[block], text=block.text,
                    png_path="", char_count=len(block.text))

    return [page(n) for n in range(1, 5)]
