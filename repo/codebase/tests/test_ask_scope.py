"""Chat có phạm vi: "giải thích trang 15" chỉ được trả lời từ trang 15.

Rò một trang ngoài phạm vi ở đây nguy hiểm hơn ở summarize/quiz, vì người dùng
đọc câu trả lời như thể nó nói về phần họ vừa hỏi. `verify.check_citation` chỉ
kiểm được trích dẫn nằm trong ĐOẠN ĐÃ TÌM — nên nếu đoạn đã tìm sai ngay từ đầu
thì không còn lớp nào bắt được.

Không lời gọi AI nào: chỉ kiểm phần lọc đoạn, chạy trước khi model được gọi.
"""

from tools import ask


def test_no_scope_searches_the_whole_document(doc):
    """Hành vi cũ phải giữ nguyên: 'attention là gì' tìm khắp tài liệu."""
    chunks = ask._chunks_in_scope(doc, None, None)
    assert {c.page_no for c in chunks} == {1, 2, 3, 4}


def test_page_scope_keeps_only_that_page(doc):
    chunks = ask._chunks_in_scope(doc, "page", "3")
    assert {c.page_no for c in chunks} == {3}


def test_chapter_scope_keeps_only_its_pages(doc):
    chunks = ask._chunks_in_scope(doc, "chapter", "ch01")
    assert {c.page_no for c in chunks} == {1, 2, 3}


def test_page_range_scope_keeps_only_its_span(doc):
    chunks = ask._chunks_in_scope(doc, "pages", "2-3")
    assert {c.page_no for c in chunks} == {2, 3}


def test_image_only_page_leaves_nothing_to_answer_from(doc):
    """Trang toàn hình không sinh chunk nào ⇒ ask phải từ chối, không đoán từ trang bên."""
    assert ask._chunks_in_scope(doc, "page", "5") == []


def test_unknown_chapter_leaves_nothing_rather_than_everything(doc):
    """Phạm vi không tồn tại phải ra rỗng — trả cả tài liệu ở đây là rò phạm vi im lặng."""
    assert ask._chunks_in_scope(doc, "chapter", "ch99") == []
