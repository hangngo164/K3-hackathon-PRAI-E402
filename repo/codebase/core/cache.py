"""Đọc/ghi .cache/ và sinh khoá theo nội dung.

Thiết kế: ARCHITECHTURE.md §13. Không biết nội dung nghĩa là gì — serde ở models.py
(STRUCTURE.md §3).

Layout:  .cache/<doc_hash>/{source.pdf, doc.json, png/, summaries/, quizzes/}
Khoá:    hash(nội dung) + prompt_version + model  => sửa prompt là tự invalidate đúng phần
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import CACHE_DIR
from .models import Document, document_from_dict, document_to_dict


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def content_key(*parts: str) -> str:
    """Khoá ổn định cho một scope + prompt_version + model."""
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest()[:16]


def doc_dir(doc_hash: str) -> Path:
    path = CACHE_DIR / doc_hash
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def save_document(document: Document) -> None:
    """Ghi vào .cache/<doc_hash>/doc.json — ĐÚNG chỗ mà load_document tìm."""
    save_json(doc_dir(document.doc_hash) / "doc.json", document_to_dict(document))


def load_document(doc_hash: str) -> Document | None:
    raw = load_json(CACHE_DIR / doc_hash / "doc.json")
    return document_from_dict(raw) if raw else None
