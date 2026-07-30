"""Đọc/ghi .cache/ và sinh khoá theo nội dung.

TODO(CP2). Thiết kế: ARCHITECHTURE.md §13.
Không biết nội dung nghĩa là gì — chỉ lưu và lấy ra.

Layout:  .cache/<doc_hash>/{source.pdf, doc.json, png/, summaries/, quizzes/, manifest.json}
Khoá:    hash(nội dung) + prompt_version + model  => sửa prompt là tự invalidate đúng phần
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def file_hash(data: bytes) -> str:
    raise NotImplementedError("TODO(CP2): sha256(data).hexdigest()[:16]")


def content_key(*parts: str) -> str:
    """Khoá ổn định cho một scope + prompt + model."""
    raise NotImplementedError("TODO(CP2)")


def doc_dir(doc_hash: str) -> Path:
    """Trả thư mục của tài liệu, tạo nếu chưa có."""
    raise NotImplementedError("TODO(CP2)")


def load_json(path: Path) -> Any | None:
    raise NotImplementedError("TODO(CP2): None nếu chưa có, không ném lỗi")


def save_json(path: Path, obj: Any) -> None:
    raise NotImplementedError("TODO(CP2): ghi UTF-8, ensure_ascii=False, tạo thư mục cha")
