# STRUCTURE — cấu trúc thư mục repo nộp bài

> **Đây là nguồn sự thật duy nhất về cấu trúc thư mục.** `ARCHITECHTURE.md` §16 trỏ về file này; `codebase/README.md` cũng trỏ về đây. Thêm/đổi/xoá file thì sửa ở đây trước, đừng để hai nơi mô tả khác nhau.
> Thiết kế từng phần chạy thế nào: `ARCHITECHTURE.md`. Danh sách tính năng: `FEATURE.md`.

---

## 1. "Tool / system prompt / agent" nằm ở đâu

Đọc mục này trước khi tìm folder `agents/` hay `tools/` — chúng không tồn tại, và đó là chủ ý.

| Khái niệm | Chỗ của nó trong repo này |
|---|---|
| **System prompt** | `codebase/prompts/*.vN.md` — mỗi file có mục `# SYSTEM` và `# USER`. Prompt là file có version, không phải string trong code |
| **Tool / function calling** | **Không dùng.** Model không được chọn hành động. Người dùng bấm scope trên UI → `core/scope.py` cắt văn bản → model chỉ trả JSON đúng schema. Thứ gần "tool" nhất là hợp đồng output: `core/schemas.py` |
| **Agent loop** | **Không có.** Hai pipeline cố định: tóm tắt (map-reduce) và quiz (generate → verify → repair). Vòng lặp duy nhất là verify→repair, **do code điều khiển, tối đa 1 lượt** |
| **Retrieval / vector DB** | **Không dùng.** Scope là cấu trúc tài liệu (chương/mục/trang/đoạn bôi đen), không phải kết quả tìm kiếm |

Lý do: mỗi lần model tự chọn hành động là thêm một chỗ nó sai được mà golden set không đo được — trong khi R4 chấm bằng % qua bộ case. Chat hỏi tự do trên tài liệu là **non-goal #1** trong `FEATURE.md`.

Nếu sau hackathon muốn thêm agent thật, điểm mở rộng là `core/tools.py` + registry. **Đừng tạo trước.**

---

## 2. Cây thư mục đầy đủ

`✓` đã có trên đĩa · `CPn` mốc tạo file · `(auto)` tự sinh, không commit.

```
repo/                                   ← root repo nộp bài
├── README.md                    ✓  thành viên (mã HV + tên) + phân công có tên
├── spec.md                      ✓  AI Spec §1-§9 — deliverable trung tâm
├── STRUCTURE.md                 ✓  file này
├── demo-slides.md → .pdf        ✓  slide 6 trang, nộp bản PDF trước CP6
├── .gitignore                   ✓
│
├── codebase/
│   ├── app.py                   ✓  CP2 thay bằng layout thật (~120 dòng: chỉ điều phối, không logic)
│   ├── check_env.py             ✓  kiểm python/package/key/LibreOffice/quyền ghi
│   ├── requirements.txt         ✓
│   ├── .env                     ✓  (auto, gitignore) key thật
│   ├── .env.example             ✓  mẫu + giải thích từng ngưỡng
│   ├── README.md                ✓  cách cài và chạy
│   ├── .streamlit/              ✓  config.toml · secrets.toml.example
│   │
│   ├── core/                       logic thuần Python — KHÔNG import streamlit
│   │   ├── config.py            ✓  đọc .env, mọi ngưỡng một chỗ
│   │   ├── errors.py            ✓  bộ exception dùng chung, map về 4 lớp chỗ khó
│   │   ├── models.py            CP2  Block · Page · Section · Chapter · Document · Anchor · ScopeContext
│   │   ├── cache.py             CP2  .cache/<doc_hash>/ · khoá = hash nội dung + prompt_ver + model
│   │   ├── ingest.py            CP2  PDF → Page/Block + bbox · lọc header/footer lặp
│   │   ├── render.py            CP2  trang → PNG · pdf_to_px() · draw_highlight()
│   │   ├── schemas.py           CP3  JSON schema output: summary · quiz item
│   │   ├── llm.py               CP3  OpenAI adapter: nạp prompt · json_schema strict · retry · usage
│   │   ├── log.py               CP3  JSONL trace → ../eval/traces/
│   │   ├── verify.py            CP3  quote khớp nguồn · anchor hợp lệ · luật quiz rác
│   │   ├── scope.py             CP3 selection+page → CP4 section/chapter/document + map-reduce
│   │   ├── summarize.py         CP3 selection+page → CP4 các tầng trên
│   │   ├── quiz.py              CP3 selection → CP4 theo mục/tài liệu (hạn ngạch theo chương)
│   │   ├── outline.py           CP4  thang 4 bậc: toc → heuristic → llm → flat
│   │   └── convert.py           CP5  PPTX → PDF (soffice) + fallback python-pptx
│   │
│   ├── prompts/                    system prompt, có version — đổi prompt là tăng version
│   │   ├── summarize.v1.md      CP3
│   │   ├── quiz.v1.md           CP3  có {{repair_feedback}} → dùng lại cho vòng sửa
│   │   └── outline.v1.md        CP4
│   │
│   ├── ui/                         chỉ layout + session_state, không logic
│   │   ├── state.py             CP2  khoá session_state + get/set
│   │   ├── sidebar.py           CP2  upload · cây outline · trạng thái key · cost phiên
│   │   ├── viewer.py            CP2  ảnh trang + overlay vàng + block picker + điều hướng
│   │   ├── panel_summary.py     CP3
│   │   └── panel_quiz.py        CP3  hiện câu hỏi · chấm · "xem chỗ này" · 👍👎
│   │
│   ├── tests/
│   │   ├── conftest.py          CP2  fixture Document mẫu
│   │   ├── test_bbox_scale.py   CP2  highlight vẽ đúng chỗ — lỗi hay gặp nhất
│   │   ├── test_ingest.py       CP2
│   │   ├── test_verify.py       CP3  quote bịa phải bị loại
│   │   ├── test_scope.py        CP4  map-reduce không rò trang ngoài scope
│   │   └── fixtures/
│   │       ├── slide-demo.pdf         CP2  deck 5-10 trang tự tạo
│   │       └── slide-hinh-only.pdf    CP2  1 trang toàn hình → test abstain lớp ①
│   │
│   ├── .cache/                  (auto, gitignore)  PDF đã convert · doc.json · png/ · summaries/ · quizzes/
│   └── .venv/                   (auto, gitignore)
│
├── eval/
│   ├── README.md                ✓  quy tắc chấm
│   ├── golden-set.csv           ✓  ≥20 case — cột đã chuẩn, dùng luôn, KHÔNG thêm file YAML
│   ├── results.md               ✓  quality bar + bảng các lượt chạy + phân tích case fail
│   ├── run.py                   CP4  đọc golden-set.csv → gọi core/ → ghi runs/ + results.md
│   ├── runs/                    CP4  một file mỗi lượt chạy
│   └── traces/                  (auto)  JSONL mọi lời gọi AI — bằng chứng "AI chạy thật" cho CP3
│
├── validation/
│   └── feedback-log.md          ✓  ≥5 người thử, quote nguyên văn
│
└── reflection/
    └── <ten-thanh-vien>.md         mỗi người một file
```

---

## 3. Trách nhiệm từng module

Cột "Không được làm" quan trọng ngang cột trách nhiệm — nó là thứ giữ file khỏi phình thành nơi chứa tất cả.

### core/

| File | Trách nhiệm | Không được làm | Phụ thuộc |
|---|---|---|---|
| `config.py` | Đọc `.env`, giữ mọi ngưỡng + đường dẫn chuẩn | Không chứa logic nghiệp vụ | dotenv |
| `errors.py` | Bộ exception dùng chung, mỗi lớp chỗ khó một loại | Không import module nào khác trong core | — |
| `models.py` | Kiểu dữ liệu + serde JSON cho cache | Không parse PDF, không gọi AI | — |
| `cache.py` | Đọc/ghi `.cache/`, sinh khoá theo nội dung | Không biết nội dung nghĩa là gì | config, models |
| `ingest.py` | File → `Document` (trang, khối, bbox) | Không render ảnh, không dò chương/mục | models, render, cache, convert |
| `render.py` | Trang → PNG · đổi toạ độ pdf→px · vẽ overlay highlight | Không đọc text | config |
| `outline.py` | Dò chương/mục theo thang 4 bậc | Không sửa `Page`/`Block` | models, llm |
| `scope.py` | `(scope, target)` → văn bản + ngân sách token + chiến lược | Không gọi AI | models, config, errors |
| `schemas.py` | JSON schema output (hợp đồng duy nhất) | Không chứa prompt | — |
| `llm.py` | Nơi **duy nhất** biết đến OpenAI: nạp prompt, gọi, retry, đếm token | Không biết summary/quiz là gì | config, log, errors |
| `summarize.py` | Ghép scope + prompt → bản tóm tắt, gộp map-reduce | Không tự cắt văn bản (việc của scope) | scope, llm, schemas, verify, cache |
| `quiz.py` | Sinh câu hỏi, hạn ngạch độ khó/chương, vòng repair | Không tự kiểm trích dẫn (việc của verify) | scope, llm, schemas, verify, cache |
| `verify.py` | Kiểm bằng **code**, không bằng model | Không gọi AI, không sửa nội dung | models, errors |
| `log.py` | Ghi JSONL trace | Không quyết định ghi gì có ý nghĩa | config |
| `convert.py` | PPTX → PDF | Không parse text | config, errors |

### ui/

| File | Trách nhiệm | Không được làm |
|---|---|---|
| `state.py` | Khai báo khoá `session_state` + get/set có kiểm tra | Không gọi core trực tiếp |
| `sidebar.py` | Upload · cây outline · trạng thái key · cost phiên | Không xử lý file |
| `viewer.py` | Ảnh trang + overlay + block picker + điều hướng | Không gọi AI |
| `panel_summary.py` / `panel_quiz.py` | Hiển thị kết quả + nút hành động | Không tự gọi model — gọi qua `core/` |
| `app.py` (root) | Layout `st.columns([3,2])` + điều phối | Không chứa logic nghiệp vụ |

---

## 4. Luật phụ thuộc

1. **`core/` không import `streamlit`.** Vi phạm một lần là `eval/run.py` chết, và mất bảng đo cho R4.
2. `ui/` import `core/` — không bao giờ ngược lại.
3. `app.py` chỉ nối `ui/` với `core/`, không chứa logic.
4. `errors.py` và `schemas.py` là lá — không import module nào khác trong `core/`.
5. `eval/run.py` nằm ngoài `codebase/` nên phải tự thêm đường import ở đầu file:
   ```python
   sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "codebase"))
   ```

---

## 5. Quy ước đặt tên

| Loại | Quy ước | Ví dụ |
|---|---|---|
| `unit_id` | `doc` · `ch<NN>` · `ch<NN>-s<NN>` · `p<NN>` · `p<NN>-b<NN>` | `ch02-s03`, `p06-b03` |
| Số trang | luôn 1-based, khớp số người dùng thấy và số trong trích dẫn `[trang 6]` | |
| Prompt | `<tên>.v<N>.md`, tăng N khi đổi nội dung + ghi `spec.md §9` | `quiz.v2.md` |
| Cache key | `hash(nội dung scope) + prompt_version + model` | `summaries/p06__quiz.v1__gpt-4o-mini.json` |
| Trace | `eval/traces/YYYY-MM-DD.jsonl`, một dòng một lời gọi | |
| Lượt eval | `eval/runs/YYYY-MM-DD-runN.md` | `2026-07-31-run2.md` |
| Test | `test_<module>.py`, một file cho một module core | `test_verify.py` |
| Biến env | CHỮ_HOA_GẠCH_DƯỚI, khai đủ trong `.env.example` | `MIN_CHARS_PER_PAGE` |

---

## 6. File không bao giờ commit

| Mục | Vì sao |
|---|---|
| `codebase/.env`, `.streamlit/secrets.toml` | chứa API key |
| `codebase/.venv/` | môi trường theo máy |
| `codebase/.cache/` | chứa **nguyên văn tài liệu đã nạp** — vi phạm luật data nếu lọt lên repo |
| `data/` của chương trình | luật bảo mật: repo nộp bài chỉ chứa trích dẫn ngắn + mã đoạn |

Đã cấu hình trong `repo/.gitignore`. Kiểm lại trước mỗi lần commit: `git status --short` không được thấy 4 mục trên.

`eval/traces/` **có** commit (bằng chứng AI chạy thật) — nhưng để `TRACE_INCLUDE_TEXT=0` để trace chỉ ghi độ dài + 200 ký tự đầu, và rà lại trước khi push.

---

## 7. Thứ tự tạo file theo mốc

| Mốc | File mới | Chạy được gì sau đó |
|---|---|---|
| **CP2** | `models.py` `cache.py` `ingest.py` `render.py` · `ui/state.py` `sidebar.py` `viewer.py` · `app.py` (viết lại) · `tests/conftest.py` `test_bbox_scale.py` `test_ingest.py` + 2 fixture PDF | Upload PDF → lật trang → tick khối → thấy overlay vàng. Tóm tắt/quiz trả dữ liệu giả cứng |
| **CP3** | `schemas.py` `llm.py` `log.py` `verify.py` `scope.py` `summarize.py` `quiz.py` · `prompts/summarize.v1.md` `quiz.v1.md` · `ui/panel_summary.py` `panel_quiz.py` · `test_verify.py` | AI thật cho scope `selection` + `page`, có verify + trace. Chạy tay 10-20 input, đặt tên nhóm lỗi |
| **CP4** | `outline.py` · `prompts/outline.v1.md` · `eval/run.py` · `test_scope.py` | Đủ 5 tầng tóm tắt + 3 kiểu quiz. Golden set ≥20 case, quality bar bằng % |
| **CP5** | `convert.py` | Nhập PPTX. Đo trọn bộ ≥2 lượt, sửa theo feedback 5 người thử |

Sau CP4 **không thêm file tính năng mới** — chỉ sửa lỗi và đo lại.
