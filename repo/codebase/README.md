# Trợ lý Ôn Slide — codebase

Nạp nhiều file slide, chọn file muốn ôn, rồi làm ba việc trên nó: **tóm tắt**
(đoạn bôi đen / trang / mục / chương / toàn bộ), **tạo quiz** có trích dẫn trang,
và **hỏi đáp** tự do về nội dung tài liệu.

Mọi output đều mang neo nguồn `[trang N]` và đi qua một lớp kiểm bằng code trước
khi tới màn hình. Cái gì không neo được thì bị loại, và hệ thống nói rõ đã loại
bao nhiêu — không im lặng hiển thị ít hơn.

## Cài đặt và chạy

Yêu cầu: Python >= 3.10 (đã kiểm với 3.12.6). LibreOffice là tuỳ chọn — chỉ cần
cho đường nhập PPTX.

```powershell
cd repo\codebase

# 1. venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # bị chặn: Set-ExecutionPolicy -Scope Process RemoteSigned

# 2. package
pip install -r requirements.txt

# 3. key
Copy-Item .env.example .env           # rồi mở .env điền OPENAI_API_KEY

# 4. kiểm môi trường
python check_env.py                   # thêm --models để xem model account đang có
python check_env.py --ping            # gọi thật 1 lời gọi rẻ, xác nhận key chạy

# 5. chạy app
streamlit run app/main.py

# 6. test
python -m pytest tests -q
```

Không kích hoạt venv thì gọi trực tiếp: `.\.venv\Scripts\python.exe check_env.py`

## Cấu trúc

```
agent_core/   logic thuần Python — không streamlit, không biết provider nào
app/          Streamlit: layout + session_state
prompts/      system prompt, có version (<tên>.vN.md)
providers/    tầng duy nhất biết đến OpenAI
tools/        ba việc người dùng bấm được: summarize · quiz · ask
```

Cây đầy đủ + trách nhiệm từng file + luật phụ thuộc: **`../STRUCTURE.md`**.

Bốn điều cần nhớ khi viết code ở đây:

1. Phụ thuộc đi **một chiều**: `app/` → `tools/` → `providers/` → `agent_core/`.
   `agent_core/` không import `streamlit` và không import `providers/`. Vi phạm
   là mất khả năng chạy pipeline ngoài Streamlit.
2. Model **không chọn hành động**. Người dùng bấm trên UI, `tools/` quyết định
   gọi gì, model chỉ điền JSON đúng schema trong `agent_core/schemas.py`. Nhờ
   vậy mọi đường đi đều liệt kê được và đo được.
3. Prompt là **file có version** trong `prompts/`. Đổi nội dung thì tạo `.v2.md`,
   không sửa tại chỗ — kết quả trong `eval/runs/` luôn gắn với một version.
4. Không tin output của model. `agent_core/verify.py` kiểm bằng code: quote phải
   khớp nguồn, anchor phải nằm trong phạm vi, câu quiz phải qua bộ luật chống
   câu hỏi rác.

## Ba tool

| Tool | Phạm vi | Cách chạy |
|---|---|---|
| `summarize` | selection · page · section · chapter · document | vượt `MAX_DIRECT_TOKENS` thì map-reduce: tóm tắt từng trang (có cache) rồi gộp |
| `quiz` | như trên | `document` **luôn** chia theo chương/phần, mỗi phần một hạn ngạch, rồi trộn — nhồi cả tài liệu vào một prompt thì câu hỏi dồn về đầu |
| `ask` | tự tìm bằng BM25 | không tìm được đoạn nào thì từ chối **không gọi model** |

Khác biệt đáng chú ý: `summarize`/`quiz` chạy trên phạm vi người dùng chọn nên
`agent_core/scope.py` biết trước được phép neo vào đâu. `ask` là đường duy nhất
mà phạm vi hợp lệ là *kết quả tìm kiếm* — nên nó dùng `agent_core/retrieve.py`
và `verify.check_citation` thay vì `check_anchor`.

## Biến môi trường

Tạo `.env` cục bộ, không commit API key. Giải thích từng ngưỡng: xem `.env.example`.

| Biến | Dùng cho |
|---|---|
| `OPENAI_API_KEY` | bắt buộc |
| `LLM_PROVIDER` | `openai` (mặc định). Thêm provider = thêm file trong `providers/` |
| `OPENAI_MODEL_FAST` / `OPENAI_MODEL_MAIN` | phân tầng: tóm tắt trang / gộp cuối + quiz + chat |
| `PAGE_DPI` | độ nét ảnh trang slide (mặc định 110) |
| `MIN_CHARS_PER_PAGE` | ngưỡng abstain cho trang thiên về hình |
| `MAX_DIRECT_TOKENS` / `MAX_JOB_CALLS` | chặn chi phí map-reduce |
| `CHAT_TOP_K` / `CHAT_MIN_SCORE` | số đoạn và ngưỡng điểm khi tìm cho chat |
| `TRACE_INCLUDE_TEXT` | có ghi nguyên văn scope vào trace hay không |

## Cache

`.cache/<doc_hash>/` chứa PDF đã convert, `doc.json`, ảnh trang, và kết quả đã
sinh (`summaries/`, `quizzes/`, `answers/`). Khoá theo **nội dung** + prompt
version + model, nên đổi tên file slide không làm mất cache, còn sửa prompt thì
tự invalidate đúng phần liên quan.

`doc.json` có `ingest_version` (`agent_core/cache.py`). Đổi cách parse thì **tăng
số đó**, nếu không thì cache cũ vẫn được nạp và tính năng mới im lặng chạy trên
dữ liệu thiếu.

Thư mục này **không commit**: nó chứa nguyên văn tài liệu người dùng nạp.

## Log/trace AI

Mọi lời gọi AI ghi một dòng JSONL tại `../eval/traces/YYYY-MM-DD.jsonl` (model,
prompt version, token vào/ra, token đã cache, latency, số lần thử) — đây là bằng
chứng "AI chạy thật". Sidebar đọc lại chính file này để hiện chi phí trong ngày.

`TRACE_INCLUDE_TEXT=0` (mặc định) chỉ ghi độ dài và 200 ký tự đầu; bật `=1` khi
cần debug và **rà lại trước khi commit**.

Trace cũng ghi `verify_fail` (mỗi lần một bullet/câu hỏi bị loại và lý do) và
`feedback` (👍/👎 trên từng câu quiz) — mỗi 👎 là một ứng viên case cho golden set.

## Giới hạn đã biết

- **Bôi đen theo khối, không quét được nửa câu.** Hệ quả của Streamlit; anchor
  thu được giống hệt thứ selection thật sẽ cho nên nâng cấp sau không phải sửa
  `agent_core/`.
- **Không đọc được chữ trong ảnh.** Trang toàn sơ đồ ⇒ abstain và nói lý do,
  không đoán từ tiêu đề.
- **Chat tìm bằng từ khoá (BM25), không phải embedding.** Đã bỏ dấu tiếng Việt
  nên gõ không dấu vẫn tìm được, nhưng hỏi bằng từ đồng nghĩa mà slide không
  dùng thì sẽ trượt — khi đó hệ thống trả "không tìm thấy" chứ không bịa.
- **Một số PDF có lỗi font** làm mất dấu cách giữa từ (`"Bộmã hóa"`). Đó là dữ
  liệu gốc của file; trích xuất đang trung thực với nó.
