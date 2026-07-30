"""Ghi JSONL trace mọi lời gọi AI — bằng chứng "AI chạy thật".

Đích: `../eval/traces/YYYY-MM-DD.jsonl`, một dòng một sự kiện.
Không quyết định ghi gì có ý nghĩa — chỉ ghi thứ được đưa.

TRACE_INCLUDE_TEXT=0 (mặc định): nguyên văn tài liệu KHÔNG vào trace, chỉ còn
độ dài + 200 ký tự đầu. Nhờ vậy `eval/traces/` commit được mà không lộ nội dung
tài liệu người dùng nạp.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timezone
from typing import Any

from .config import TRACES_DIR, settings

_LOCK = threading.Lock()  # map-reduce chạy ThreadPoolExecutor => nhiều thread cùng ghi một file
_TEXT_FIELDS = ("source_text", "text", "question", "answer", "user_prompt", "quote", "message")
_PREVIEW_CHARS = 200


def enabled() -> bool:
    """Tắt trace khi chạy test: TRACE_DISABLE=1."""
    return os.getenv("TRACE_DISABLE", "").strip() != "1"


def _redact(fields: dict[str, Any]) -> dict[str, Any]:
    """Cắt các trường chứa nguyên văn tài liệu khi TRACE_INCLUDE_TEXT=0."""
    if settings().trace_include_text:
        return fields
    out = dict(fields)
    for key in _TEXT_FIELDS:
        value = out.get(key)
        if isinstance(value, str):
            out[key] = value[:_PREVIEW_CHARS]
            out[f"{key}_len"] = len(value)
    return out


def trace(kind: str, **fields: Any) -> None:
    """kind: 'llm_call' · 'verify_fail' · 'ingest' · 'feedback' · 'job' · 'route'.

    Không bao giờ làm hỏng luồng chính: ghi trace lỗi thì nuốt, vì mất một dòng
    log rẻ hơn nhiều so với việc người dùng mất kết quả đang chạy dở.
    """
    if not enabled():
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        **_redact(fields),
    }
    path = TRACES_DIR / f"{date.today().isoformat()}.jsonl"
    try:
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def session_cost(day: date | None = None) -> dict[str, int]:
    """Tổng lời gọi/token trong ngày — sidebar hiển thị để nhóm biết đang đốt gì.

    Đọc lại từ file chứ không giữ biến đếm trong RAM: Streamlit rerun liên tục
    và `eval/run.py` chạy ở tiến trình riêng — file là nguồn sự thật chung.
    """
    path = TRACES_DIR / f"{(day or date.today()).isoformat()}.jsonl"
    totals = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cached_tokens": 0}
    if not path.exists():
        return totals
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # dòng ghi dở do tắt app giữa chừng — bỏ qua, không chết
            if record.get("kind") != "llm_call":
                continue
            totals["calls"] += 1
            for key in ("tokens_in", "tokens_out", "cached_tokens"):
                totals[key] += int(record.get(key) or 0)
    return totals


def trace_path(day: date | None = None) -> str:
    return str(TRACES_DIR / f"{(day or date.today()).isoformat()}.jsonl")
