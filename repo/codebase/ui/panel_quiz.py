"""Tab Quiz: sinh câu hỏi, làm, chấm, xem giải thích có trích dẫn, 👍👎.

TODO(CP3). Tính năng F2.1-F2.6 (FEATURE.md §4).
Không tự gọi model — gọi qua core.quiz.

Bốn thứ không được thiếu:
  · mỗi câu hiện [trang N] bấm được (F2.5) — điều kiện để quiz là AUGMENT
  · chấm xong tổng kết theo trang/mục cần ôn lại (F2.4) — "kết quả" của lát cắt
  · số câu thực tế nói thật khi verify loại item ("4/5 câu có căn cứ")
  · 👎 => "sai chỗ nào?" ghi eval/feedback.jsonl (F2.6, HAX G15)
"""

from __future__ import annotations


def render() -> None:
    raise NotImplementedError("TODO(CP3)")
