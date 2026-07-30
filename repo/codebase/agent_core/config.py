"""Đọc .env và giữ mọi ngưỡng + đường dẫn chuẩn ở một chỗ.

Đổi hành vi hệ thống thì sửa .env, không đi tìm số magic trong code.
Không chứa logic nghiệp vụ. Thiết kế: ARCHITECHTURE.md §17.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# --- Đường dẫn chuẩn (mọi module dùng chung, không tự ghép path) ---
CODEBASE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = CODEBASE_DIR.parent
CACHE_DIR = CODEBASE_DIR / ".cache"
PROMPTS_DIR = CODEBASE_DIR / "prompts"
EVAL_DIR = REPO_ROOT / "eval"
TRACES_DIR = EVAL_DIR / "traces"

load_dotenv(CODEBASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_api_key: str
    model_fast: str
    model_main: str
    page_dpi: int
    min_chars_per_page: int
    max_direct_tokens: int
    max_job_calls: int
    request_timeout_s: int
    trace_include_text: bool
    chat_top_k: int
    chat_min_score: float

    @property
    def has_api_key(self) -> bool:
        return bool(self.openai_api_key) and not self.openai_api_key.startswith("sk-thay-bang")

    def model_for(self, tier: str) -> str:
        """tier: 'fast' = tóm tắt trang · 'main' = reduce cuối + sinh quiz."""
        return self.model_main if tier == "main" else self.model_fast

    def problems(self) -> list[str]:
        """Vấn đề cấu hình — check_env.py và app.py hiển thị nguyên văn."""
        out: list[str] = []
        if not self.has_api_key:
            out.append("Chưa có OPENAI_API_KEY thật (Copy-Item .env.example .env rồi điền key).")
        if not self.model_fast or not self.model_main:
            out.append("Thiếu OPENAI_MODEL_FAST / OPENAI_MODEL_MAIN.")
        if self.page_dpi < 72:
            out.append(f"PAGE_DPI={self.page_dpi} quá thấp, chữ trên slide sẽ không đọc được.")
        return out


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings(
        llm_provider=os.getenv("LLM_PROVIDER", "openai").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        model_fast=os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini").strip(),
        model_main=os.getenv("OPENAI_MODEL_MAIN", "gpt-4o").strip(),
        page_dpi=_int("PAGE_DPI", 110),
        min_chars_per_page=_int("MIN_CHARS_PER_PAGE", 120),
        max_direct_tokens=_int("MAX_DIRECT_TOKENS", 6000),
        max_job_calls=_int("MAX_JOB_CALLS", 60),
        request_timeout_s=_int("REQUEST_TIMEOUT_S", 60),
        trace_include_text=os.getenv("TRACE_INCLUDE_TEXT", "0").strip() == "1",
        chat_top_k=_int("CHAT_TOP_K", 6),
        chat_min_score=_float("CHAT_MIN_SCORE", 0.08),
    )


def reset_settings_cache() -> None:
    """Gọi sau khi app.py đẩy st.secrets vào os.environ."""
    settings.cache_clear()
