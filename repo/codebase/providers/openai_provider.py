"""Nơi DUY NHẤT trong code biết đến OpenAI.

Không biết summary/quiz/chat là gì — nhận system+user+schema, trả JSON đã parse.
Mọi thứ nghiệp vụ nằm ở `tools/`; mọi thứ điều phối (prompt, retry, trace) nằm
ở `providers/__init__.py`.

Prompt caching: `providers/__init__.py` render user text với phần bất biến
(chỉ dẫn + văn bản nguồn) đặt TRƯỚC, phần thay đổi (số câu, repair_feedback)
đặt SAU — cache của OpenAI ăn theo tiền tố, nên thứ tự khối trong `prompts/`
là một quyết định về tiền, không phải thẩm mỹ.
"""

from __future__ import annotations

import json
import time
from typing import Any

from agent_core.config import settings
from agent_core.errors import LLMError, SchemaError, TransientLLMError

from .base import Provider, RawResult


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - requirements.txt đã pin
            raise LLMError(
                user_message="Thiếu package `openai`. Chạy: pip install -r requirements.txt"
            ) from exc
        self._client = OpenAI(api_key=api_key or settings().openai_api_key)

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
        started = time.monotonic()
        try:
            response = self._create(
                system=system,
                user=user,
                schema=schema,
                schema_name=schema_name,
                model=model,
                timeout_s=timeout_s,
                temperature=temperature,
            )
        except Exception as exc:
            raise self._translate(exc, model) from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        choice = response.choices[0]

        # Model từ chối trả lời (safety) — KHÔNG phải lỗi hệ thống, và không
        # được nuốt thành JSON rỗng: tầng trên cần biết để nói thật với người dùng.
        refusal = getattr(choice.message, "refusal", None)
        if refusal:
            raise LLMError(user_message=f"Model từ chối yêu cầu này: {refusal}")

        content = choice.message.content or ""
        if not content.strip():
            raise SchemaError(user_message="Model trả về nội dung rỗng.")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise SchemaError(
                user_message=f"Model trả JSON không parse được: {content[:200]}"
            ) from exc
        if not isinstance(data, dict):
            raise SchemaError(user_message="Model trả JSON không phải object.")

        usage = getattr(response, "usage", None)
        details = getattr(usage, "prompt_tokens_details", None) if usage else None
        return RawResult(
            data=data,
            model=getattr(response, "model", model),
            tokens_in=int(getattr(usage, "prompt_tokens", 0) or 0),
            tokens_out=int(getattr(usage, "completion_tokens", 0) or 0),
            cached_tokens=int(getattr(details, "cached_tokens", 0) or 0),
            latency_ms=latency_ms,
        )

    def _create(self, *, system, user, schema, schema_name, model, timeout_s, temperature):
        """Gọi Chat Completions với `json_schema` strict.

        `strict: true` buộc output khớp schema ở phía OpenAI — nhờ vậy
        `agent_core/verify.py` chỉ phải lo tính ĐÚNG của nội dung, không phải
        lo hình dạng JSON.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
            "timeout": timeout_s,
            "temperature": temperature,
        }
        try:
            return self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            # Model dòng reasoning không nhận `temperature` — thử lại một lần
            # không kèm tham số đó thay vì bắt người dùng đổi model trong .env.
            if "temperature" in str(exc).lower():
                kwargs.pop("temperature", None)
                return self._client.chat.completions.create(**kwargs)
            raise

    @staticmethod
    def _translate(exc: Exception, model: str) -> Exception:
        """Đổi exception của SDK sang bộ lỗi của app, tách rõ cái nào đáng retry."""
        import openai

        if isinstance(exc, (openai.RateLimitError, openai.APITimeoutError,
                            openai.APIConnectionError, openai.InternalServerError)):
            return TransientLLMError(user_message=f"Tạm thời gọi AI không được: {exc}")
        if isinstance(exc, openai.AuthenticationError):
            return LLMError(user_message="OPENAI_API_KEY không hợp lệ — kiểm lại file .env.")
        if isinstance(exc, openai.PermissionDeniedError):
            return LLMError(
                user_message=f"Account không có quyền dùng model '{model}'. "
                             f"Xem model khả dụng: python check_env.py --models"
            )
        if isinstance(exc, openai.NotFoundError):
            return LLMError(
                user_message=f"Không có model tên '{model}'. Sửa OPENAI_MODEL_* trong .env."
            )
        if isinstance(exc, openai.BadRequestError):
            return LLMError(user_message=f"Yêu cầu gửi lên không hợp lệ: {exc}")
        if isinstance(exc, openai.APIStatusError) and 500 <= getattr(exc, "status_code", 0) < 600:
            return TransientLLMError(user_message=f"Lỗi phía OpenAI: {exc}")
        return LLMError(user_message=f"Gọi AI thất bại: {exc}")

    def list_models(self) -> list[str]:
        try:
            return sorted(m.id for m in self._client.models.list().data)
        except Exception as exc:
            raise self._translate(exc, "-") from exc
