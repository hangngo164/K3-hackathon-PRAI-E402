"""Nạp và render prompt từ `prompts/<id>.vN.md`.

Prompt là FILE CÓ VERSION, không phải string trong code: kết quả eval luôn gắn
với một version cụ thể, và đổi prompt là tự invalidate đúng phần cache (khoá
cache có prompt_version — xem `cache.content_key`).

Mỗi file có hai mục `# SYSTEM` và `# USER`. Comment HTML trong file là ghi chú
cho người đọc repo, KHÔNG gửi cho model — nên bị lột ở đây.

Không biết provider nào đang dùng: chỉ trả ra text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from .config import PROMPTS_DIR
from .errors import AppError

_FILENAME_RE = re.compile(r"^(?P<pid>.+)\.v(?P<ver>\d+)\.md$")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADING_RE = re.compile(r"^#[ \t]+(SYSTEM|USER)[ \t]*$", re.MULTILINE)
_VAR_RE = re.compile(r"\{\{[ \t]*(\w+)[ \t]*\}\}")


@dataclass(frozen=True)
class Prompt:
    prompt_id: str
    version: str  # "v1" — đi vào trace và vào khoá cache
    system: str
    user_template: str


def available_versions(prompt_id: str) -> list[int]:
    versions: list[int] = []
    for path in PROMPTS_DIR.glob(f"{prompt_id}.v*.md"):
        match = _FILENAME_RE.match(path.name)
        if match and match.group("pid") == prompt_id:
            versions.append(int(match.group("ver")))
    return sorted(versions)


@lru_cache(maxsize=32)
def load(prompt_id: str, version: int | None = None) -> Prompt:
    """Không truyền version thì lấy version CAO NHẤT có trong thư mục."""
    versions = available_versions(prompt_id)
    if not versions:
        raise AppError(user_message=f"Không tìm thấy prompt '{prompt_id}' trong {PROMPTS_DIR}.")
    chosen = versions[-1] if version is None else version
    if chosen not in versions:
        raise AppError(
            user_message=f"Prompt '{prompt_id}' không có v{chosen} (đang có: {versions})."
        )

    raw = (PROMPTS_DIR / f"{prompt_id}.v{chosen}.md").read_text(encoding="utf-8")
    system, user = _split_sections(_COMMENT_RE.sub("", raw))
    if not system.strip():
        raise AppError(user_message=f"Prompt '{prompt_id}.v{chosen}' thiếu mục '# SYSTEM'.")
    return Prompt(prompt_id=prompt_id, version=f"v{chosen}", system=system, user_template=user)


def _split_sections(text: str) -> tuple[str, str]:
    """Cắt theo hai heading `# SYSTEM` / `# USER`, giữ nguyên phần thân."""
    sections: dict[str, str] = {}
    headings = list(_HEADING_RE.finditer(text))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        sections[heading.group(1)] = text[heading.end():end].strip()
    return sections.get("SYSTEM", ""), sections.get("USER", "")


def render(template: str, variables: dict[str, str]) -> str:
    """Thay `{{ten_bien}}` bằng giá trị.

    KHÔNG dùng `str.format`: prompt chứa dấu ngoặc nhọn của ví dụ JSON, format
    sẽ nổ hoặc nuốt mất chúng.

    Biến thiếu => chuỗi rỗng, không ném lỗi: phần lớn biến là tuỳ chọn
    (`repair_feedback` ở lượt sinh đầu, `context_text` khi scope không có lân cận)
    và để trống là hợp lệ.
    """
    return _VAR_RE.sub(lambda m: str(variables.get(m.group(1), "")), template)


def missing_variables(template: str, variables: dict[str, str]) -> list[str]:
    """Biến có trong template mà caller không truyền — `tests` dùng để bắt lỗi gõ nhầm."""
    return sorted({name for name in _VAR_RE.findall(template) if name not in variables})
