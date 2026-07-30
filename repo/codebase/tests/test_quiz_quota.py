"""Hạn ngạch câu hỏi — thứ giữ cho quiz cả tài liệu không dồn vào chương đầu.

Đây là lý do quiz toàn tài liệu gọi nhiều lượt sinh theo phần thay vì nhồi cả
tài liệu vào một prompt: phủ đều phải là phép chia của code, không phải thiện
chí của model.
"""

from tools.quiz import MAX_PART_SHARE, allocate_quota

_PARTS = [("chapter", "ch01", "A"), ("chapter", "ch02", "B"), ("chapter", "ch03", "C")]


def test_every_part_gets_at_least_one_question():
    quota = allocate_quota(_PARTS, weights=[30, 5, 2], n_items=10)
    assert min(quota) >= 1
    assert sum(quota) == 10


def test_biggest_part_cannot_dominate():
    """Chương dài gấp 15 lần vẫn không được nuốt quá 40% bộ đề."""
    quota = allocate_quota(_PARTS, weights=[30, 1, 1], n_items=10)
    assert max(quota) <= int(10 * MAX_PART_SHARE)


def test_total_always_matches_request():
    for n_items in (4, 5, 7, 12, 15):
        quota = allocate_quota(_PARTS, weights=[10, 6, 3], n_items=n_items)
        assert sum(quota) == n_items, f"n_items={n_items} ra {quota}"


def test_fewer_questions_than_parts_prefers_bigger_parts():
    quota = allocate_quota(_PARTS, weights=[2, 40, 9], n_items=2)
    assert sum(quota) == 2
    assert quota[1] == 1 and quota[2] == 1  # bỏ phần nhỏ nhất, không chia đều cho có
    assert quota[0] == 0


def test_single_part_takes_everything():
    assert allocate_quota([_PARTS[0]], weights=[10], n_items=5) == [5]


def test_no_parts_returns_empty():
    assert allocate_quota([], weights=[], n_items=5) == []
