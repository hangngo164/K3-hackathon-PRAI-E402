"""Kiểm tra môi trường trước khi build.  Chạy:  python check_env.py [--models] [--ping]

Chỉ dùng thư viện chuẩn + package bên ngoài; không import `agent_core`/`tools`
ở đầu file, để chạy được cả khi code đang hỏng và đó chính là thứ cần chẩn đoán.
Exit code 0 = sẵn sàng build, 1 = còn việc phải sửa.
"""

from __future__ import annotations

import argparse
import importlib
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGES = ["streamlit", "openai", "fitz", "pptx", "dotenv", "pytest"]
OK, WARN, BAD = "[ok]  ", "[warn]", "[BAD] "

# Console Windows mặc định cp1252, không in nổi tiếng Việt: script chẩn đoán mà
# tự chết vì UnicodeEncodeError thì mất đúng lúc cần nó nhất.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def _version(mod) -> str:
    for attr in ("__version__", "version", "VersionBind"):
        v = getattr(mod, attr, None)
        if isinstance(v, str):
            return v
    return "?"


def _check_prompts() -> list[str]:
    """Mọi prompt phải nạp được và có đủ hai mục.

    Đáng kiểm ở đây vì prompt hỏng chỉ lộ ra lúc bấm nút — tức là giữa buổi demo.
    """
    print("\n--- prompt ---")
    problems: list[str] = []
    try:
        sys.path.insert(0, str(HERE))
        from agent_core import prompting
    except Exception as exc:  # noqa: BLE001
        print(f"{BAD}không import được agent_core.prompting: {exc}")
        return ["agent_core/prompting.py không import được — xem lỗi ngay trên."]

    for prompt_id in ("route", "summarize", "quiz", "ask", "outline"):
        try:
            prompt = prompting.load(prompt_id)
        except Exception as exc:  # noqa: BLE001
            print(f"{BAD}{prompt_id:<10} {exc}")
            problems.append(f"Prompt '{prompt_id}' không nạp được.")
            continue
        if not prompt.user_template.strip():
            print(f"{WARN}{prompt_id:<10} {prompt.version} — mục '# USER' rỗng")
        else:
            print(f"{OK}{prompt_id:<10} {prompt.version}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", action="store_true", help="liệt kê model id account đang có")
    ap.add_argument("--ping", action="store_true", help="gọi thật 1 lời gọi rẻ để xác nhận key chạy")
    args = ap.parse_args()

    problems: list[str] = []
    print(f"{OK}python {sys.version.split()[0]}  ({sys.executable})")
    if sys.version_info < (3, 10):
        problems.append("Cần Python >= 3.10.")

    print("\n--- package ---")
    for name in PACKAGES:
        try:
            mod = importlib.import_module(name)
            print(f"{OK}{name:<12} {_version(mod)}")
        except ImportError:
            print(f"{BAD}{name:<12} chưa cài")
            problems.append(f"Thiếu {name} — chạy: pip install -r requirements.txt")

    print("\n--- cấu hình ---")
    try:
        from dotenv import load_dotenv

        load_dotenv(HERE / ".env")
    except ImportError:
        pass

    if (HERE / ".env").exists():
        print(f"{OK}.env có mặt")
    else:
        print(f"{BAD}.env chưa có")
        problems.append("Chưa có .env — chạy: Copy-Item .env.example .env  rồi điền key.")

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.startswith("sk-thay-bang"):
        print(f"{BAD}OPENAI_API_KEY chưa điền key thật")
        problems.append("Điền OPENAI_API_KEY thật vào .env.")
    elif not key.startswith("sk-"):
        print(f"{WARN}OPENAI_API_KEY không bắt đầu bằng 'sk-' — kiểm lại đã copy đủ chưa")
    else:
        print(f"{OK}OPENAI_API_KEY ...{key[-4:]} (dài {len(key)})")

    print(f"{OK}model FAST = {os.getenv('OPENAI_MODEL_FAST', '(chưa đặt)')}")
    print(f"{OK}model MAIN = {os.getenv('OPENAI_MODEL_MAIN', '(chưa đặt)')}")

    print("\n--- công cụ ngoài ---")
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if soffice:
        print(f"{OK}LibreOffice: {soffice}  (convert PPTX -> PDF chạy được)")
    else:
        print(f"{WARN}Không thấy LibreOffice (soffice) — đường PPTX sẽ dùng fallback python-pptx")
        print("       (không chặn build; muốn có: winget install TheDocumentFoundation.LibreOffice)")

    print("\n--- thư mục ---")
    cache = HERE / ".cache"
    try:
        (cache / "png").mkdir(parents=True, exist_ok=True)
        (cache / ".write-test").write_text("ok", encoding="utf-8")
        (cache / ".write-test").unlink()
        print(f"{OK}.cache/ ghi được")
    except OSError as exc:
        print(f"{BAD}.cache/ không ghi được: {exc}")
        problems.append("Không ghi được .cache/ — kiểm quyền thư mục.")

    traces = HERE.parent / "eval" / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    print(f"{OK}eval/traces/ sẵn sàng ({traces})")

    print("\n--- cấu trúc agent ---")
    for folder in ("agent_core", "app", "prompts", "providers", "tools"):
        if (HERE / folder).is_dir():
            print(f"{OK}{folder}/")
        else:
            print(f"{BAD}{folder}/ không có")
            problems.append(f"Thiếu thư mục {folder}/ — repo bị lệch so với STRUCTURE.md.")

    problems += _check_prompts()

    if args.models or args.ping:
        print("\n--- gọi OpenAI ---")
        try:
            from openai import OpenAI

            client = OpenAI(api_key=key, timeout=30)
            if args.models:
                ids = sorted(m.id for m in client.models.list())
                print(f"{OK}{len(ids)} model khả dụng. Vài cái hay dùng:")
                for mid in ids:
                    if mid.startswith(("gpt-", "o1", "o3", "o4")):
                        print(f"       {mid}")
            if args.ping:
                fast = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
                resp = client.chat.completions.create(
                    model=fast,
                    messages=[{"role": "user", "content": "Trả lời đúng một từ: OK"}],
                    max_completion_tokens=5,
                )
                usage = resp.usage
                print(f"{OK}ping {fast} -> {resp.choices[0].message.content!r} "
                      f"(in={usage.prompt_tokens} out={usage.completion_tokens})")
        except Exception as exc:  # noqa: BLE001 — báo nguyên văn cho người dùng tự sửa
            print(f"{BAD}{type(exc).__name__}: {exc}")
            problems.append("Lời gọi OpenAI thất bại — xem thông báo lỗi ngay trên.")

    print()
    if problems:
        print("CHƯA SẴN SÀNG:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("MÔI TRƯỜNG SẴN SÀNG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
