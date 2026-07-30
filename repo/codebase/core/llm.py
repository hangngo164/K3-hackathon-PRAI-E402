"""Nơi DUY NHẤT trong code biết đến OpenAI.

TODO(CP3). Thiết kế: ARCHITECHTURE.md §12.
Không biết summary/quiz là gì — chỉ nạp prompt, gọi model, trả JSON đã parse.
Đổi provider = sửa file này, prompt và schema không đổi.

Prompt caching: đặt phần bất biến (chỉ dẫn + văn bản tài liệu) TRƯỚC,
phần thay đổi (scope, số câu) SAU — cache của OpenAI ăn theo tiền tố.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResult:
    data: dict
    model: str
    prompt_id: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    cached_tokens: int
    latency_ms: int
    attempts: int


def load_prompt(prompt_id: str) -> tuple[str, str, str]:
    """Đọc prompts/<prompt_id>.vN.md → (system, user_template, version).

    Không truyền version thì lấy version cao nhất có trong thư mục.
    File có hai mục: `# SYSTEM` và `# USER`.
    """
    raise NotImplementedError("TODO(CP3)")


def render_prompt(template: str, variables: dict[str, str]) -> str:
    """Thay {{ten_bien}} — không dùng str.format vì prompt có dấu ngoặc nhọn của JSON."""
    raise NotImplementedError("TODO(CP3)")


def complete_json(
    prompt_id: str,
    variables: dict[str, str],
    schema: dict,
    *,
    tier: str = "fast",
) -> LLMResult:
    """Gọi model với response_format json_schema strict.

    Retry 3 lần (backoff) cho 429/5xx/timeout. JSON sai schema => 1 lượt repair,
    không retry mù. Mỗi lời gọi ghi một dòng trace qua log.py.
    """
    raise NotImplementedError("TODO(CP3)")
