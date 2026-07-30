"""PPTX → PDF, để phía sau chỉ có MỘT pipeline duy nhất.

TODO(CP5). Thiết kế + rủi ro: ARCHITECHTURE.md §6.
Không parse text (việc của ingest.py).

    a) soffice --headless --convert-to pdf --outdir <cache> file.pptx   (đường chính)
    b) fallback python-pptx: text theo shape, KHÔNG có layout — bản xuống cấp,
       UI phải nói rõ cho người dùng biết

RỦI RO DEMO: máy cần có LibreOffice. check_env.py cảnh báo sớm; luôn convert
sẵn file demo ra PDF làm backup (02-guide.md §5.2).
"""

from __future__ import annotations

from pathlib import Path


def has_libreoffice() -> bool:
    raise NotImplementedError("TODO(CP5): shutil.which('soffice')")


def pptx_to_pdf(pptx_path: Path, out_dir: Path) -> Path:
    """Ném ConvertError nếu cả hai đường đều không được."""
    raise NotImplementedError("TODO(CP5)")


def pptx_text_fallback(pptx_path: Path) -> list[str]:
    """python-pptx: mỗi slide một chuỗi text, không layout, không bbox thật."""
    raise NotImplementedError("TODO(CP5)")
