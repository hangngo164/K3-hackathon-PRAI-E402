"""Tìm đoạn cho chat — chỗ duy nhất "phạm vi hợp lệ" là kết quả tìm kiếm.

Hai tính chất phải giữ:
  · một đoạn không bao giờ vắt qua hai trang (nếu không thì `[trang N]` mất nghĩa)
  · không tìm được thì trả rỗng, để `tools/ask.py` từ chối thay vì gọi model rồi bịa
"""

from agent_core import retrieve


def test_chunks_never_span_two_pages(doc):
    for chunk in retrieve.build_chunks(doc):
        assert all(bid.startswith(f"p{chunk.page_no:02d}-") for bid in chunk.block_ids)


def test_image_only_page_produces_no_chunk(doc):
    assert all(chunk.page_no != 5 for chunk in retrieve.build_chunks(doc))


def test_search_finds_the_right_page(doc):
    results = retrieve.search(retrieve.build_chunks(doc), "Positional Encoding là gì")
    assert results
    assert results[0].chunk.page_no == 4


def test_search_returns_nothing_for_unrelated_question(doc):
    """Hỏi thứ tài liệu không nói => rỗng => chat từ chối, không gọi model."""
    results = retrieve.search(retrieve.build_chunks(doc), "chính sách hoàn tiền của khoá học")
    assert results == []


def test_stopwords_do_not_drive_retrieval(doc):
    """Câu hỏi chỉ toàn từ nối thì không được khớp bừa vào trang nào."""
    assert retrieve.search(retrieve.build_chunks(doc), "là của và các có") == []


def test_stopwords_filtered_without_diacritics_too(doc):
    """Từ nối gõ không dấu cũng phải bị lọc — nếu không, 'la cua va' khớp mọi trang."""
    assert retrieve.search(retrieve.build_chunks(doc), "la cua va cac co") == []


def test_question_without_diacritics_still_finds_the_page(doc):
    """Rất nhiều người gõ không dấu; trượt hết là hỏng hoàn toàn chứ không phải kém đi."""
    results = retrieve.search(retrieve.build_chunks(doc), "positional encoding la gi")
    assert results and results[0].chunk.page_no == 4


def test_diacritic_folding_matches_vietnamese_terms(doc):
    with_marks = retrieve.search(retrieve.build_chunks(doc), "trọng số attention")
    without = retrieve.search(retrieve.build_chunks(doc), "trong so attention")
    assert [r.chunk.page_no for r in with_marks] == [r.chunk.page_no for r in without]


def test_allowed_unit_ids_cover_returned_chunks(doc):
    results = retrieve.search(retrieve.build_chunks(doc), "Query Key Value")
    allowed = retrieve.allowed_unit_ids(results)
    for result in results:
        assert f"p{result.chunk.page_no:02d}" in allowed
        assert all(bid in allowed for bid in result.chunk.block_ids)


def test_prompt_text_labels_page_and_blocks(doc):
    results = retrieve.search(retrieve.build_chunks(doc), "Query Key Value")
    text = retrieve.as_prompt_text(results)
    assert "[trang" in text and "khối" in text
