"""Hợp đồng output — JSON schema cho structured output.

TODO(CP3). Nội dung hợp đồng: ARCHITECHTURE.md §9 (summary) và §10 (quiz item).
File lá: không chứa prompt, không import module khác trong core/.

Đây là chỗ DUY NHẤT định nghĩa "output đúng là gì" — llm.py, verify.py và
eval/run.py đều đọc từ đây, nên đổi schema là đổi ở một chỗ.
"""

from __future__ import annotations

# Neo nguồn — dùng lại trong cả hai schema dưới
ANCHOR_SCHEMA: dict = {}  # TODO(CP3): page_no · block_ids[] · quote

SUMMARY_SCHEMA: dict = {}  # TODO(CP3): scope_label · tldr · bullets[] · key_terms[] · not_covered[] · confidence

QUIZ_SCHEMA: dict = {}  # TODO(CP3): items[] · type · stem · options · answer_index · explanation · anchor · difficulty · distractor_rationale


def bullets_range(scope: str) -> tuple[int, int]:
    """Số bullet cho phép theo scope — độ dài do code quyết, không để model tự chọn.

    selection 2-3 · page 3-5 · section 5-7 · chapter 6-9 · document 8-12
    """
    raise NotImplementedError("TODO(CP3)")


def difficulty_mix(scope: str) -> dict[str, float]:
    """Cơ cấu độ khó: selection 60/40/0 · section 40/40/20 · document 30/40/30."""
    raise NotImplementedError("TODO(CP3)")
