# Prototype Daily Quiz

## Phạm vi

- Flow end-to-end:
- Quyết định trung tâm có AI chạy thật:
- Phần mock:
- Phần chưa triển khai:

## Cài đặt và chạy

Yêu cầu: Python >= 3.10 (đã kiểm với 3.12.6). LibreOffice là tuỳ chọn — chỉ cần cho đường nhập PPTX.

```powershell
cd repo\codebase

# 1. venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # nếu bị chặn: Set-ExecutionPolicy -Scope Process RemoteSigned

# 2. package
pip install -r requirements.txt

# 3. key
Copy-Item .env.example .env           # rồi mở .env điền OPENAI_API_KEY

# 4. kiểm môi trường
python check_env.py                   # thêm --models để xem model account đang có
python check_env.py --ping            # gọi thật 1 lời gọi rẻ, xác nhận key chạy

# 5. chạy app
streamlit run app.py
```

Không kích hoạt venv thì gọi trực tiếp: `.\.venv\Scripts\python.exe check_env.py`

## Cấu trúc

Cây thư mục đầy đủ + trách nhiệm từng module + luật phụ thuộc: **`../STRUCTURE.md`**.

Ba điều cần nhớ khi viết code ở đây:

1. `core/` **không import `streamlit`** — vi phạm là `eval/run.py` chết, mất bảng đo cho R4.
2. `ui/` import `core/`, không bao giờ ngược lại. `app.py` chỉ nối hai bên, không chứa logic.
3. Prompt là file có version trong `prompts/` — đổi nội dung thì tạo `.v2.md`, không sửa tại chỗ, và ghi changelog `spec.md §9`.

Mỗi module chưa viết đều có sẵn docstring nói rõ trách nhiệm, ranh giới ("không được làm gì") và mốc phải xong (`TODO(CP2)` / `TODO(CP3)` ...).

## Biến môi trường

Tạo `.env` cục bộ và không commit API key. Danh sách biến + ý nghĩa từng ngưỡng: xem `.env.example`.

| Biến | Dùng cho |
|---|---|
| `OPENAI_API_KEY` | bắt buộc |
| `OPENAI_MODEL_FAST` / `OPENAI_MODEL_MAIN` | phân tầng model: tóm tắt trang / sinh quiz |
| `PAGE_DPI` | độ nét ảnh trang slide (mặc định 110) |
| `MIN_CHARS_PER_PAGE` | ngưỡng abstain cho trang thiên về hình |
| `MIN_WORDS_PER_SELECTION` | ngưỡng hỏi lại khi đoạn bôi đen quá ngắn |
| `MAX_DIRECT_TOKENS` / `MAX_JOB_CALLS` | chặn chi phí map-reduce |
| `TRACE_INCLUDE_TEXT` | có ghi nguyên văn scope vào trace hay không |

## Log/trace AI

Mọi lời gọi AI ghi một dòng JSONL tại `../eval/traces/YYYY-MM-DD.jsonl` (kèm model, prompt version, token, latency) — đây là bằng chứng "AI chạy thật" cho CP3.

`TRACE_INCLUDE_TEXT=0` (mặc định) chỉ ghi độ dài và 200 ký tự đầu của scope; bật `=1` khi cần debug và **rà lại trước khi commit** theo luật bảo mật data.
