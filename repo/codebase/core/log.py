"""Ghi JSONL trace mọi lời gọi AI — bằng chứng "AI chạy thật" cho CP3.

TODO(CP3). Đích: ../eval/traces/YYYY-MM-DD.jsonl, một dòng một lời gọi.
Không quyết định ghi gì có ý nghĩa — chỉ ghi thứ được đưa.

TRACE_INCLUDE_TEXT=0 (mặc định): chỉ ghi độ dài + 200 ký tự đầu của scope,
để trace commit được mà không lộ nguyên văn tài liệu (luật bảo mật data).
"""

from __future__ import annotations

from typing import Any


def trace(kind: str, **fields: Any) -> None:
    """kind: 'llm_call' · 'verify_fail' · 'ingest' · 'feedback'."""
    raise NotImplementedError("TODO(CP3)")


def session_cost() -> dict[str, int]:
    """Tổng lời gọi/token trong ngày — sidebar hiển thị để nhóm biết đang đốt gì."""
    raise NotImplementedError("TODO(CP3)")
