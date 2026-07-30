"""Tầng provider: chọn nhà cung cấp, nạp prompt, gọi, retry, ghi trace.

`tools/` chỉ cần một hàm duy nhất ở đây:

    result = providers.complete_json("summarize", variables, SUMMARY_SCHEMA, "summary")

và không bao giờ biết đang chạy OpenAI hay gì khác. Đổi provider = đổi
`LLM_PROVIDER` trong `.env`, prompt và schema giữ nguyên.

Import openai được làm LƯỜI trong `get_provider()`: `import providers` phải rẻ
để test chạy được trên máy chưa cài SDK.
"""

from __future__ import annotations

import random
import time
from functools import lru_cache
from typing import Any

from agent_core import prompting
from agent_core.config import settings
from agent_core.errors import AppError, LLMError, TransientLLMError
from agent_core.log import trace

from .base import LLMResult, Provider, RawResult

__all__ = ["LLMResult", "Provider", "RawResult", "complete_json", "get_provider", "reset_provider_cache"]

MAX_ATTEMPTS = 3
_BACKOFF_BASE_S = 1.0


@lru_cache(maxsize=4)
def get_provider(name: str | None = None) -> Provider:
    """Factory theo `LLM_PROVIDER`. Thêm provider mới = thêm một nhánh ở đây."""
    chosen = (name or settings().llm_provider).strip().lower()
    if chosen == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider()
    raise AppError(
        user_message=f"LLM_PROVIDER='{chosen}' chưa được hỗ trợ. Hiện có: openai."
    )


def reset_provider_cache() -> None:
    """Gọi sau khi đổi biến môi trường (app đẩy st.secrets vào os.environ)."""
    get_provider.cache_clear()


def complete_json(
    prompt_id: str,
    variables: dict[str, str],
    schema: dict[str, Any],
    schema_name: str,
    *,
    tier: str = "fast",
    prompt_version: int | None = None,
    temperature: float = 0.2,
) -> LLMResult:
    """Nạp `prompts/<prompt_id>.vN.md`, render biến, gọi model, trả JSON đã parse.

    Retry tối đa MAX_ATTEMPTS cho lỗi tạm thời (429/5xx/timeout) với backoff có
    jitter. JSON sai schema KHÔNG retry mù ở đây — `tools/` xử bằng một vòng
    repair có phản hồi cụ thể, vì gọi lại y nguyên thường ra y nguyên.

    Mỗi lời gọi ghi đúng một dòng trace, kể cả khi hỏng.
    """
    cfg = settings()
    if not cfg.has_api_key:
        raise LLMError(
            user_message="Chưa có OPENAI_API_KEY thật — phần gọi AI bị chặn. "
                         "Xem slide và lật trang vẫn dùng được."
        )

    prompt = prompting.load(prompt_id, prompt_version)
    user_text = prompting.render(prompt.user_template, variables)
    provider = get_provider()
    model = cfg.model_for(tier)

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = provider.complete_json(
                system=prompt.system,
                user=user_text,
                schema=schema,
                schema_name=schema_name,
                model=model,
                timeout_s=cfg.request_timeout_s,
                temperature=temperature,
            )
        except TransientLLMError as exc:
            last_error = exc
            if attempt == MAX_ATTEMPTS:
                break
            time.sleep(_BACKOFF_BASE_S * (2 ** (attempt - 1)) + random.uniform(0, 0.3))
            continue
        except Exception as exc:  # lỗi không đáng retry: key sai, model lạ, JSON hỏng
            trace(
                "llm_call",
                prompt_id=prompt_id,
                prompt_version=prompt.version,
                model=model,
                tier=tier,
                provider=provider.name,
                attempts=attempt,
                ok=False,
                error=type(exc).__name__,
                error_message=str(exc)[:300],
            )
            raise

        trace(
            "llm_call",
            prompt_id=prompt_id,
            prompt_version=prompt.version,
            model=raw.model,
            tier=tier,
            provider=provider.name,
            attempts=attempt,
            ok=True,
            tokens_in=raw.tokens_in,
            tokens_out=raw.tokens_out,
            cached_tokens=raw.cached_tokens,
            latency_ms=raw.latency_ms,
            source_text=variables.get("source_text", ""),
        )
        return LLMResult(
            data=raw.data,
            model=raw.model,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.version,
            tokens_in=raw.tokens_in,
            tokens_out=raw.tokens_out,
            cached_tokens=raw.cached_tokens,
            latency_ms=raw.latency_ms,
            attempts=attempt,
            provider=provider.name,
        )

    trace(
        "llm_call",
        prompt_id=prompt_id,
        prompt_version=prompt.version,
        model=model,
        tier=tier,
        provider=provider.name,
        attempts=MAX_ATTEMPTS,
        ok=False,
        error=type(last_error).__name__ if last_error else "Unknown",
        error_message=str(last_error)[:300],
    )
    raise LLMError(
        user_message=f"Gọi AI hỏng sau {MAX_ATTEMPTS} lần thử ({last_error}). "
                     f"Kết quả đã sinh xong vẫn giữ nguyên — thử lại phần còn thiếu."
    )
