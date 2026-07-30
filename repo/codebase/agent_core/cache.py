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


# Tăng số này khi `ingest.py` đổi cách dựng Document (thêm trường, đổi cách lọc
# khối, đổi cách tính text). Thiếu nó thì `.cache/` cũ vẫn được nạp và tính năng
# mới im lặng chạy trên dữ liệu thiếu — kiểu lỗi rất khó nhìn ra vì không có gì
# báo, chỉ là kết quả kém hơn.
#   v2: thêm is_title_like · lọc header/footer lặp · Page.text dựng từ khối
#   v3: gộp khoảng trắng trong dòng · nới ngưỡng lọc chân trang lên 200 ký tự
INGEST_VERSION = 3


def save_document(document: Document) -> None:
    """Ghi vào `.cache/<doc_hash>/doc.json` — đúng chỗ `load_document` tìm."""
    payload = document_to_dict(document)
    payload["ingest_version"] = INGEST_VERSION
    save_json(doc_dir(document.doc_hash) / "doc.json", payload)


def load_document(doc_hash: str) -> Document | None:
    """Trả None khi cache do bản ingest cũ sinh ra — caller sẽ parse lại."""
    raw = load_json(CACHE_DIR / doc_hash / "doc.json")
    if not raw or raw.get("ingest_version") != INGEST_VERSION:
        return None
    return document_from_dict(raw)


def artifact_path(doc_hash: str, kind: str, key: str) -> Path:
    """Chỗ nằm của một kết quả đã sinh: `.cache/<doc_hash>/<kind>/<key>.json`.

    `kind`: 'summaries' · 'quizzes' · 'answers'. `key` do `content_key()` sinh,
    nên hai scope có nội dung y hệt dùng chung một file — đổi tên file slide
    không làm mất cache.
    """
    return doc_dir(doc_hash) / kind / f"{key}.json"


def load_artifact(doc_hash: str, kind: str, key: str) -> Any | None:
    return load_json(artifact_path(doc_hash, kind, key))


def save_artifact(doc_hash: str, kind: str, key: str, payload: Any) -> None:
    save_json(artifact_path(doc_hash, kind, key), payload)
