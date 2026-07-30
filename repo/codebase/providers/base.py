"""Hợp đồng mà mọi provider phải theo — tầng DUY NHẤT biết đến nhà cung cấp model.

Đổi sang Anthropic/Gemini/local = thêm một file trong `providers/` và đổi
`LLM_PROVIDER` trong `.env`. KHÔNG đụng `prompts/`, `tools/`, `agent_core/`.
Đó là lý do tầng này tồn tại riêng thay vì nằm trong `agent_core/`.

File lá của tầng providers: chỉ import `agent_core.errors`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawResult:
    """Thứ một provider trả về — chưa gắn nghĩa nghiệp vụ."""

    data: dict[str, Any]
    model: str
    tokens_in: int
    tokens_out: int
    cached_tokens: int
    latency_ms: int


@dataclass(frozen=True)
class LLMResult:
    """RawResult + thông tin prompt — thứ `tools/` thực sự nhận được."""

    data: dict[str, Any]
    model: str
    prompt_id: str
    prompt_version: str
    tokens_in: int
    tokens_out: int
    cached_tokens: int
    latency_ms: int
    attempts: int
    provider: str = "openai"
    warnings: list[str] = field(default_factory=list)


class Provider(ABC):
    """Một lời gọi = system + user + JSON schema bắt buộc. Không có tự do nào khác.

    Cố ý KHÔNG có tham số `tools`/`functions` ở tầng này: model không được chọn
    hành động — người dùng chọn trên UI, `tools/` quyết định gọi gì, model chỉ
    điền nội dung vào một hợp đồng đã biết trước. Nhờ vậy mọi output đều kiểm
    được bằng code (`agent_core/verify.py`) thay vì phải tin model.
    """

    name: str = "base"

    @abstractmethod
    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        schema_name: str,
        model: str,
        timeout_s: int,
        temperature: float = 0.2,
    ) -> RawResult:
        """Trả JSON đã parse, đúng `schema`.

        Ném `TransientLLMError` cho thứ đáng thử lại (429/5xx/timeout),
        `SchemaError` khi JSON không parse được, `LLMError` cho phần còn lại.
        """

    @abstractmethod
    def list_models(self) -> list[str]:
        """Cho `check_env.py --models` — biết account đang thật sự có model nào."""
