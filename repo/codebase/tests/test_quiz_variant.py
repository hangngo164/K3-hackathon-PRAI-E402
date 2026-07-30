"""Xin quiz lần nữa phải ra bộ KHÁC — nhưng khác có kiểm soát, không phải ngẫu nhiên.

Lỗi đã gặp thật: tạo quiz toàn tài liệu ba lần ra ba bộ y hệt. Nguyên nhân là
khoá cache không phân biệt được "bộ thứ nhất" với "bộ thứ hai", nên lần hai đọc
lại đúng file JSON của lần một.

Ba tính chất phải giữ đồng thời, và file này kiểm cả ba:
  · cùng variant  ⇒ cùng khoá  ⇒ vẫn lấy được từ cache, không đốt lời gọi
  · khác variant  ⇒ khác khoá  ⇒ sinh bộ mới
  · bộ mới biết bộ cũ đã hỏi gì ⇒ đa dạng đến từ việc phủ rộng nguồn hơn,
    không từ việc nới ràng buộc

Không gọi AI: chỉ kiểm phần khoá cache và phần gom "ý đã hỏi".
"""

import pytest

from tools import quiz

_ARGS = ("nội dung phạm vi", "v2", "gpt-4o", "document", 12)


def test_same_variant_keeps_the_same_cache_key():
    """Xin lại đúng bộ cũ vẫn phải rẻ — nếu không thì mỗi lần vẽ lại là một job mới."""
    assert quiz._cache_key(*_ARGS, 0) == quiz._cache_key(*_ARGS, 0)


def test_each_variant_gets_its_own_cache_entry():
    """Đây là lỗi gốc: thiếu variant trong khoá thì lần hai đọc lại file của lần một."""
    keys = {quiz._cache_key(*_ARGS, v) for v in range(4)}
    assert len(keys) == 4


def test_variant_zero_stays_reproducible_for_eval():
    """`eval/run.py` pin variant=0, nên khoá của nó không được phụ thuộc gì ngoài đầu vào."""
    before = quiz._cache_key(*_ARGS, 0)
    quiz._cache_key(*_ARGS, 3)  # sinh bộ khác ở giữa
    assert quiz._cache_key(*_ARGS, 0) == before


def test_scope_and_count_still_separate_the_keys():
    base = quiz._cache_key(*_ARGS, 0)
    assert quiz._cache_key("nội dung phạm vi", "v2", "gpt-4o", "chapter", 12, 0) != base
    assert quiz._cache_key("nội dung phạm vi", "v2", "gpt-4o", "document", 5, 0) != base


# --- "Ý đã hỏi rồi" gom từ chính các bộ trước ---

def _fake_cache(monkeypatch, sets: dict[int, list[dict]]):
    """Giả cache: variant -> danh sách item. Khoá được tra ngược về variant."""
    keyed = {quiz._cache_key(*_ARGS, v): {"items": items} for v, items in sets.items()}
    monkeypatch.setattr(quiz.cache, "load_artifact",
                        lambda doc_hash, kind, key: keyed.get(key))


class _Ctx:
    text = "nội dung phạm vi"


def test_first_set_has_nothing_to_avoid(doc, monkeypatch):
    _fake_cache(monkeypatch, {})
    assert quiz._spent_facts(doc, _Ctx(), "v2", "gpt-4o", "document", 12, 0) == []


def test_second_set_avoids_what_the_first_asked(doc, monkeypatch):
    _fake_cache(monkeypatch, {0: [
        {"stem": "Query dùng để làm gì?", "anchor": {"quote": "Query là vector biểu diễn token"}},
        {"stem": "Key khác Value chỗ nào?", "anchor": {"quote": "Key dùng để so khớp"}},
    ]})
    facts = quiz._spent_facts(doc, _Ctx(), "v2", "gpt-4o", "document", 12, 1)
    assert len(facts) == 2
    assert "Query dùng để làm gì?" in facts[0]
    assert "Query là vector biểu diễn token" in facts[0]  # kèm nguồn để model biết chỗ đã khai thác


def test_third_set_avoids_both_earlier_sets(doc, monkeypatch):
    _fake_cache(monkeypatch, {
        0: [{"stem": "Câu bộ 1", "anchor": {"quote": "q1"}}],
        1: [{"stem": "Câu bộ 2", "anchor": {"quote": "q2"}}],
    })
    facts = quiz._spent_facts(doc, _Ctx(), "v2", "gpt-4o", "document", 12, 2)
    assert [("Câu bộ 1" in f) for f in facts].count(True) == 1
    assert [("Câu bộ 2" in f) for f in facts].count(True) == 1


def test_avoid_list_is_capped_so_it_cannot_crowd_out_the_source(doc, monkeypatch):
    """Danh sách tránh mà dài hơn nguồn thì model hết chỗ đọc chính tài liệu."""
    _fake_cache(monkeypatch, {
        v: [{"stem": f"Câu {v}-{i}", "anchor": {"quote": "q"}} for i in range(30)]
        for v in range(5)
    })
    facts = quiz._spent_facts(doc, _Ctx(), "v2", "gpt-4o", "document", 12, 5)
    assert len(facts) == quiz._MAX_AVOID_FACTS


def test_items_without_a_stem_are_skipped(doc, monkeypatch):
    _fake_cache(monkeypatch, {0: [{"stem": "", "anchor": {"quote": "q"}}, {"anchor": {}}]})
    assert quiz._spent_facts(doc, _Ctx(), "v2", "gpt-4o", "document", 12, 1) == []


# --- Quiz cả tài liệu: variant và force phải đi xuống từng phần ---

def test_parts_inherit_variant_and_force(doc, monkeypatch):
    """Thiếu chỗ này thì tầng tài liệu sinh mới, nhưng từng chương vẫn lấy bộ cũ từ cache."""
    seen: list[dict] = []

    def fake_generate(document, scope, target_id=None, n_items=5, **kwargs):
        seen.append({"scope": scope, "target_id": target_id, **kwargs})
        return {"items": [], "_meta": {}}

    monkeypatch.setattr(quiz, "generate", fake_generate)
    parts = [("chapter", "ch01", "Self-Attention"), ("chapter", "ch02", "Positional Encoding")]
    quiz._generate_by_parts(doc, parts, 6, "Toàn bộ tài liệu", None, variant=3, force=True)

    assert seen, "không phần nào được gọi"
    assert all(call["variant"] == 3 for call in seen)
    assert all(call["force"] is True for call in seen)


@pytest.mark.parametrize("variant", [0, 1, 2])
def test_the_same_variant_always_shuffles_the_same_way(doc, monkeypatch, variant):
    """Tất định trong cùng một variant — điều kiện để hai lượt eval so sánh được."""
    def fake_generate(document, scope, target_id=None, n_items=5, **kwargs):
        return {"items": [{"stem": f"{target_id}-{i}", "anchor": {"quote": f"q{i}"}}
                          for i in range(3)],
                "_meta": {}}

    monkeypatch.setattr(quiz, "generate", fake_generate)
    parts = [("chapter", "ch01", "A"), ("chapter", "ch02", "B")]

    def run():
        payload = quiz._generate_by_parts(doc, parts, 6, "Toàn bộ tài liệu", None, variant=variant)
        return [i["stem"] for i in payload["items"]]

    assert run() == run()


def test_at_least_one_variant_reorders_the_set(doc, monkeypatch):
    def fake_generate(document, scope, target_id=None, n_items=5, **kwargs):
        return {"items": [{"stem": f"{target_id}-{i}", "anchor": {"quote": f"q{i}"}}
                          for i in range(4)],
                "_meta": {}}

    monkeypatch.setattr(quiz, "generate", fake_generate)
    parts = [("chapter", "ch01", "A"), ("chapter", "ch02", "B")]
    orders = {
        tuple(i["stem"] for i in
              quiz._generate_by_parts(doc, parts, 8, "Toàn bộ", None, variant=v)["items"])
        for v in range(5)
    }
    assert len(orders) > 1, "seed không đổi theo variant — mọi bộ ra cùng thứ tự"
