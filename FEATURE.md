# FEATURES — Trợ lý Ôn Slide

> Danh sách tính năng + tiêu chí nghiệm thu từng tính năng. Cách hệ thống chạy: `ARCHITECTURE.md`. Bằng chứng, impact, lý do chọn: `spec.md`.
> **Quy ước ưu tiên:** **P0** = không có thì không demo được · **P1** = làm nếu xong P0 trước CP4 · **P2** = backlog, đưa vào slide 6 "nếu có thêm 1 tuần".

---

## 1. Phạm vi & lát cắt

**Người dùng:** học viên ôn lại một buổi đã học bằng file slide của buổi đó — trước quiz, hoặc sau khi nghe mà chưa chắc mình hiểu.

**Job (không có chữ AI):** *xác định trong tài liệu buổi học phần nào mình chưa thật hiểu, và kiểm tra lại phần đó, trong thời gian ngắn trước khi bị đánh giá.*

**Lát cắt MỘT CÂU (đường demo chính):**

> **một học viên ôn trước quiz · bôi đen một đoạn slide chưa chắc · AI sinh 5 câu hỏi kiểm tra hiểu có trích dẫn trang · học viên tự phát hiện chỗ mình hổng.**

Cả `FEATURES.md` này rộng hơn một lát cắt: 8 tính năng người dùng đối mặt. Với hackathon 1,5 ngày, chỉ **F1.5 + F2.1** (đoạn bôi đen) là lát cắt được chấm ở R2/R5 và được demo live; các scope còn lại dùng chung resolver/verifier nên gần như miễn phí về code, nhưng **không được kéo demo đi lan**. Rubric chấm chuỗi quyết định, không chấm số lượng tính năng.

**Mức tự động hoá:** tóm tắt = automate · quiz = augment (chi tiết §6).

---

## 2. Bảng tính năng tổng

| ID | Tính năng | Scope | Ưu tiên | AI thật? | Xong ở mốc |
|---|---|---|---|---|---|
| **F3.1** | Nạp file slide (PDF) | — | P0 | không | CP2 |
| **F3.2** | Hiển thị slide trong cửa sổ + điều hướng trang | — | P0 | không | CP2 |
| **F3.3** | Bôi đen đoạn trên slide (chọn khối + overlay vàng) | — | P0 | không | CP2 |
| **F3.4** | Cây chương/mục để chọn phạm vi | — | P1 | 1 lời gọi (bậc dò `llm`) | CP4 |
| **F3.5** | Nạp file PPTX | — | P1 | không | CP5 |
| **F3.6** | Xuất tóm tắt / quiz ra file | — | P2 | không | — |
| **F1.5** | Tóm tắt **phần bôi đen** | `selection` | **P0** | có | CP3 |
| **F1.4** | Tóm tắt **từng trang** | `page` | **P0** | có | CP3 |
| **F1.3** | Tóm tắt **từng mục** | `section` | P1 | có | CP4 |
| **F1.2** | Tóm tắt **từng chương** | `section→chapter` | P1 | có | CP4 |
| **F1.1** | Tóm tắt **toàn bộ tài liệu** | `document` | P1 | có | CP4 |
| **F2.1** | Quiz từ **đoạn bôi đen** | `selection` | **P0** | có | CP3 |
| **F2.2** | Quiz theo **từng phần** (trang/mục/chương) | `page/section/chapter` | P1 | có | CP4 |
| **F2.3** | Quiz **tổng hợp cả tài liệu** | `document` | P1 | có | CP4 |
| **F2.4** | Làm quiz + chấm + xem giải thích có trích dẫn | — | P0 | không | CP3 |
| **F2.5** | Nhảy tới nguồn của câu hỏi ("xem chỗ này") | — | P0 | không | CP3 |
| **F2.6** | 👍/👎 "sai chỗ nào?" trên từng câu | — | P1 | không | CP5 |
| **F4.1** | Cache theo nội dung | — | P0 | — | CP3 |
| **F4.2** | Trace mọi lời gọi AI + đếm token/cost | — | P0 | — | CP3 |
| **F4.3** | Eval runner chạy golden set | — | P0 | — | CP4 |

Ba dòng in đậm ở cột ưu tiên là **đường demo**: hỏng cái nào thì không có gì để trình bày.

---

## 3. Nhóm F1 — Tóm tắt

Mọi tính năng nhóm này dùng cùng một hợp đồng output (`tldr` · `bullets` có neo nguồn · `key_terms` · `not_covered` · `confidence`) và cùng một verifier. Khác nhau đúng ba thứ: **phạm vi văn bản, số bullet, chiến lược gọi model.**

### F1.5 · Tóm tắt phần bôi đen *(P0)*

| | |
|---|---|
| Input | 1-n khối văn bản đã chọn trên một trang (+1 khối liền kề mỗi phía làm ngữ cảnh, không tóm tắt vào) |
| Output | 1 câu TL;DR + 2-3 bullet + thuật ngữ trong đoạn, mỗi bullet có `[trang N]` |
| Hiển thị | Panel phải, cạnh slide đang bôi vàng — người dùng thấy đoạn gốc và bản tóm tắt cùng lúc |
| Thiếu căn cứ | Đoạn < ~40 từ hữu ích ⇒ không tóm tắt, hỏi lại: *"Đoạn này ngắn (8 từ) — mở rộng ra cả trang?"* |
| Nghiệm thu | (a) 100% bullet có quote khớp nguyên văn nguồn · (b) không bullet nào dùng thông tin ngoài đoạn+ngữ cảnh · (c) tổng độ dài tóm tắt ≤ 60% độ dài đoạn gốc · (d) thuật ngữ EN giữ nguyên, không tự dịch |

### F1.4 · Tóm tắt từng trang *(P0)*

| | |
|---|---|
| Input | `Page.text` của trang đang xem |
| Output | TL;DR + 3-5 bullet + `not_covered` |
| Đặc thù | Trang thiên về hình (`char_count` < ngưỡng) ⇒ **abstain**: *"Trang 12 chủ yếu là sơ đồ — mình không đọc được nội dung trong ảnh."* Đây là case golden set bắt buộc của lớp ① |
| Nghiệm thu | (a) như F1.5 (a)(b)(d) · (b) trang toàn hình phải abstain, không được tóm tắt bừa từ tiêu đề · (c) `not_covered` nêu đúng phần không đọc được khi trang có cả chữ lẫn hình |

### F1.3 · Tóm tắt từng mục *(P1)*

| | |
|---|---|
| Input | các trang trong `page_range` của mục |
| Output | TL;DR + 5-7 bullet, mỗi bullet neo về trang cụ thể trong mục |
| Đặc thù | < 6k token ⇒ một lời gọi; lớn hơn ⇒ map-reduce từ tóm tắt trang (tái dùng cache) |
| Nghiệm thu | (a) mỗi bullet neo về một trang **thuộc mục đó** · (b) không bỏ sót trang nào có nội dung: mỗi trang trong mục xuất hiện ở ≥1 bullet hoặc được nêu trong `not_covered` |

### F1.2 · Tóm tắt từng chương *(P1)*

| | |
|---|---|
| Input | tóm tắt các mục con (cache) + danh sách tiêu đề trang |
| Output | TL;DR + 6-9 bullet + danh sách mục con kèm khoảng trang |
| Nghiệm thu | (a) mọi mục con xuất hiện trong output · (b) neo trang vẫn truy được về trang gốc, không neo về "tóm tắt của tóm tắt" |

### F1.1 · Tóm tắt toàn bộ tài liệu *(P1)*

| | |
|---|---|
| Input | tóm tắt các chương (cache); tài liệu `flat` ⇒ reduce trực tiếp từ tóm tắt trang |
| Output | TL;DR + 8-12 bullet + bản đồ chương/mục kèm khoảng trang |
| Đặc thù | Tài liệu lớn: báo trước *"~45 trang, khoảng N lời gọi, ~X giây"* và chờ xác nhận. Chạy song song 4 luồng, có progress `st.status` theo trang |
| Nghiệm thu | (a) mọi chương có mặt · (b) không bullet nào chỉ đến trang không tồn tại · (c) chạy lại lần 2 dùng cache, thời gian < 3s |

**Hành vi chung nhóm F1:** mỗi bullet có nút *"xem chỗ này"* → nhảy viewer về đúng trang và bôi vàng đúng khối (F2.5 dùng chung cơ chế). Đây là điều kiện để tóm tắt được phép **automate**: người dùng kiểm được trong một cú bấm.

---

## 4. Nhóm F2 — Quiz ôn tập

### F2.1 · Quiz từ đoạn bôi đen *(P0 — lõi lát cắt)*

| | |
|---|---|
| Input | đoạn bôi đen + số câu (3/5/8, mặc định 5) |
| Output | n câu (MCQ 4 phương án / đúng-sai / trả lời ngắn), mỗi câu có `answer`, `explanation`, `anchor [trang N]`, `distractor_rationale`, nhãn độ khó |
| Cơ cấu | ~60% recall · 40% understand |
| Đoạn quá ngắn | Tạo tối đa số câu chống đỡ được và **nói rõ**: *"Đoạn này chỉ đủ căn cứ cho 2 câu — mình tạo 2 câu thay vì 5."* Không nhồi câu trùng ý |
| Nghiệm thu | (a) mỗi câu có quote khớp nguồn, suy ra được đáp án từ quote · (b) đúng 1 đáp án đúng, nhiễu sai kiểm chứng được theo nguồn · (c) không câu nào hỏi về hình thức tài liệu ("trang này có mấy bullet") · (d) độ dài phương án chênh ≤ 2.5× · (e) `stem` không lộ đáp án |

### F2.2 · Quiz theo từng phần *(P1)*

| | |
|---|---|
| Input | scope = trang / mục / chương + số câu (5-8) |
| Cơ cấu | 40% recall · 40% understand · 20% apply |
| Đặc thù | Hạn ngạch chia theo trang/mục **trước khi sinh** — nếu để model tự chọn, câu hỏi dồn hết vào phần đầu |
| Nghiệm thu | (a) như F2.1 · (b) mỗi trang có nội dung trong scope đóng góp ≤ 40% số câu · (c) không hai câu hỏi cùng một fact |

### F2.3 · Quiz tổng hợp cả tài liệu *(P1)*

| | |
|---|---|
| Input | scope = `document` + số câu (10-15) |
| Cơ cấu | 30% recall · 40% understand · 30% apply; **bắt buộc phủ đều các chương** |
| Đặc thù | Với tài liệu lớn, sinh theo từng chương (hạn ngạch) rồi trộn — không nhồi cả tài liệu vào một prompt |
| Nghiệm thu | (a) như F2.1 · (b) mỗi chương có ≥1 câu · (c) chương chiếm nhiều trang nhất không quá 40% số câu · (d) thứ tự câu trộn, không đi tuần tự theo trang |

### F2.4 · Làm quiz, chấm, xem giải thích *(P0)*

Không phải tính năng AI — nhưng thiếu nó thì quiz chỉ là một danh sách chữ, không phải công cụ *tự phát hiện chỗ hổng* như lát cắt đã hứa.

- Chọn phương án → chấm ngay → hiện đáp án + `explanation` + trích dẫn nguồn.
- Cuối bộ: *"Bạn đúng 3/5. Hai câu sai đều thuộc trang 6 — phần Query/Key/Value."* ⇒ đúng "kết quả" trong lát cắt.
- Nghiệm thu: (a) tổng kết chỉ đúng phần cần ôn lại theo trang/mục có thật · (b) không tiết lộ đáp án trước khi trả lời · (c) làm lại được bộ cũ mà không cần gọi AI lần nữa (đọc từ cache).

### F2.5 · Nhảy tới nguồn *(P0)*

Bấm `[trang 6]` trên một câu hỏi hoặc một bullet ⇒ viewer về trang 6, bôi vàng đúng khối. Nghiệm thu: 100% neo bấm được và bôi đúng khối đã trích (test bằng `test_bbox_scale.py` + kiểm tay 10 neo).

### F2.6 · Feedback 👍/👎 *(P1)*

👎 mở một dòng chọn nhanh: *sai kiến thức · nhiều đáp án đúng · câu hỏi vô nghĩa · không có trong slide · quá dễ*. Ghi vào `eval/feedback.jsonl` kèm `item_id`, scope, prompt version.
Giá trị: mỗi 👎 là một ứng viên case cho golden set và một dòng cho `validation/` — thu bằng chứng ngay trong flow (HAX **G15**), không phải phỏng vấn lại sau.

---

## 5. Nhóm F3 — UI & Viewer

### F3.1 · Nạp file slide (PDF) *(P0)*
`st.file_uploader` → hash → ingest (parse + render tất cả trang) → hiện trang 1. Có progress; deck 40 trang xong trong ~5-15s.
Nghiệm thu: (a) nạp lại cùng file lần 2 dùng cache, < 1s · (b) file không phải PDF/PPTX, PDF hỏng, PDF có mật khẩu ⇒ báo đúng nguyên nhân, app không crash.

### F3.2 · Hiển thị slide trong cửa sổ *(P0)*
Ảnh trang render đúng layout gốc (không phải text trần), nút ◀ ▶, nhảy tới số trang, chỉ báo `6/40`. Bố cục `st.columns([3,2])`: trái slide, phải panel Tóm tắt/Quiz — **xem và ôn cùng lúc, không phải đổi tab.**
Nghiệm thu: (a) chữ trên slide đọc được ở kích thước mặc định · (b) lật trang không kéo cả trang rerun (dùng `st.fragment`) · (c) đúng số trang khớp số trang trong trích dẫn.

### F3.3 · Bôi đen đoạn trên slide *(P0)*
Danh sách khối văn bản của trang hiện tại, mỗi khối một checkbox kèm 60 ký tự đầu; tick ⇒ **vẽ overlay vàng lên đúng vị trí khối trên ảnh slide** ⇒ hai nút [Tóm tắt đoạn này] [Tạo quiz từ đoạn này].
Nghiệm thu: (a) overlay trùng khít khối văn bản (sai lệch < 5px trên fixture) · (b) chọn nhiều khối không liền nhau vẫn được · (c) đổi trang thì xoá selection cũ và nói rõ.
**Giới hạn phải nói khi demo:** chọn theo *khối*, không quét được nửa câu — hệ quả của Streamlit, không phải thiếu sót thiết kế. Bản bắt selection thật bằng chuột là P2 (`ARCHITECTURE.md §7` Tầng 2).

### F3.4 · Cây chương/mục *(P1)*
Sidebar hiện `Chương 2 › Mục 3 (trang 12-18)`; bấm để đặt scope cho panel. Tài liệu không tách được chương/mục ⇒ hiện lý do và **disable** F1.2/F1.3 kèm giải thích, không hiện nút bấm vào ra rác (HAX **G1**).
Nghiệm thu: (a) khoảng trang của mọi mục liền nhau, không chồng lấn, phủ hết tài liệu · (b) `outline_source` hiện cho người dùng thấy (mục lục PDF / tự dò / AI dò).

### F3.5 · Nạp file PPTX *(P1)*
Convert bằng LibreOffice headless, fallback `python-pptx` (text theo shape, không layout — nói rõ trên UI là bản xuống cấp).
Nghiệm thu: (a) PPTX 20 trang ra đúng 20 trang, thứ tự đúng · (b) máy không có `soffice` ⇒ cảnh báo ngay lúc mở app, không phải lúc đang demo.

### F3.6 · Xuất kết quả *(P2)*
Tải tóm tắt (.md có trích dẫn trang) / quiz (.md hai bản: đề và đáp án). Nghiệm thu: mở bằng editor khác vẫn giữ nguyên trích dẫn `[trang N]`.

---

## 6. Mức tự động hoá theo cost-of-error

| Tính năng | Mức | Sai thì ai chịu gì — sửa đắt hay rẻ |
|---|---|---|
| F1.x Tóm tắt | **Automate** | Bullet lệch ý: học viên bấm "xem chỗ này" là thấy ngay nguồn ngay cạnh. Sai rẻ, tự sửa được trong một cú bấm ⇒ không cần chặn bằng người duyệt |
| F2.x Quiz | **Augment** | Đáp án sai **dạy học viên kiến thức sai** trước kỳ đánh giá — sửa đắt, và người học không có cách biết mình vừa học sai. Vì vậy: mọi câu luôn hiện trích dẫn trước khi tin, có 👎, và UI nói rõ "câu hỏi do AI sinh từ slide của bạn — kiểm trích dẫn nếu thấy lạ" |
| F1.4/F1.5 khi nguồn mỏng | **Conditional** | Đủ căn cứ thì làm; không đủ thì abstain và hỏi lại, không đoán (HAX **G10**) |
| F3.4 dò chương/mục | **Automate + sửa được** | Dò sai chỉ làm scope lệch, người dùng đổi scope tay được (P2: sửa outline) |

---

## 7. Non-goals — những thứ **không** build

1. **Chatbot Q&A tự do trên tài liệu.** Mọi lời gọi AI bị đóng khung trong scope người dùng chọn. Đây là lựa chọn thiết kế: scope xác định ⇒ kiểm được trích dẫn ⇒ đo được.
2. **Trả lời kiến thức ngoài slide đã nạp.** Không tra web, không dùng kiến thức nền của model. Hỏi ngoài phạm vi ⇒ từ chối gọn + đưa việc làm được.
3. **Chấm điểm / theo dõi tiến độ học viên.** Quiz là để người học tự kiểm, không phải để đánh giá ai.
4. **Đăng nhập, tài khoản, nhiều người dùng, đồng bộ nhiều máy.** Không DB, cache theo máy.
5. **OCR / đọc nội dung trong ảnh và công thức dạng ảnh.** Trang toàn hình ⇒ abstain và nói thật.
6. **Đoán đề thi / xác định "phần nào sẽ thi".** Không có căn cứ trong tài liệu.
7. **Sinh slide, sửa slide, dịch tài liệu.**
8. **Deploy, domain, hạ tầng production.** Chạy local `streamlit run app.py`.

---

## 8. Bốn đường đi của trải nghiệm

Bảng này là bản đối chiếu cho `spec.md §6`; hành vi kỹ thuật tương ứng ở `ARCHITECTURE.md §14`.

| Đường đi | Tình huống | Người dùng thấy gì | Làm gì tiếp được |
|---|---|---|---|
| **Happy path** | Bôi đen khối "Query/Key/Value" trang 6, xin 5 câu | 5 câu, mỗi câu có `[trang 6]`, làm xong được chấm + tổng kết chỗ hổng | Bấm "xem chỗ này" · tạo thêm câu khó hơn · tóm tắt cùng đoạn |
| **Low-confidence (②)** | Bôi đen một dòng tiêu đề 8 từ | *"Đoạn này ngắn (8 từ) — mình tạo được 2 câu, hoặc mở rộng ra cả trang cho 5 câu?"* + hai nút chọn | Chọn 2 câu · mở rộng scope · chọn khối khác |
| **Không có căn cứ (①)** | Xin tóm tắt trang 12 chỉ có sơ đồ | *"Trang 12 chủ yếu là sơ đồ — mình không đọc được nội dung trong ảnh, nên không tóm tắt để tránh nói sai."* | Xem trang lân cận · gõ lại nội dung sơ đồ · chọn cả mục |
| **Correction (user sửa)** | Câu 3 có 2 phương án đúng | 👎 → *"sai chỗ nào?"* → chọn "nhiều đáp án đúng" | Sinh lại đúng câu đó · loại câu · ghi vào `eval/feedback.jsonl` |
| **Ngoài phạm vi (③)** | "Giải hộ bài tập trang 20" | *"Mình chỉ làm việc trên slide bạn đã nạp — tóm tắt và tạo câu hỏi ôn. Tạo quiz phần trang 20 để bạn tự thử nhé?"* | Nhận đề nghị · chọn scope khác |
| **Đặc thù domain (④)** | Slide viết "attention", model định dịch "sự chú ý" | Thuật ngữ giữ nguyên như slide; `key_terms` hiện song song EN + giải thích VN | Bấm thuật ngữ để về đúng trang định nghĩa |
| **Lỗi hệ thống** | Hết quota / mất mạng giữa lúc tóm tắt toàn bộ | Nêu đúng nguyên nhân + **giữ phần đã sinh xong** + viewer/outline vẫn dùng được | Thử lại phần thiếu · dùng kết quả đã cache |

---

## 9. Definition of done cho demo *(CP6)*

- [ ] Nạp `slide-demo.pdf` → 40 trang hiện đúng layout, lật trang mượt
- [ ] Bôi đen 2 khối trang 6 → overlay vàng trùng khít
- [ ] Sinh 5 câu quiz có trích dẫn, làm bộ đó, tổng kết chỉ đúng chỗ hổng theo trang
- [ ] **Case chỗ khó live:** tóm tắt trang toàn hình → hệ thống abstain và nói lý do *(case này nên demo, không nên giấu — `02-guide.md §5.1` slide 3)*
- [ ] Tóm tắt toàn tài liệu chạy được, có tiến độ, lần 2 lấy cache < 3s
- [ ] Golden set ≥20 case, ≥2 lượt chạy trong `eval/runs/`, đối chiếu quality bar đã chốt 23:59 N1
- [ ] Backup: screenshot/video ngắn + PDF đã convert sẵn từ PPTX
- [ ] Mỗi thành viên giải thích được phần có tên mình (vibe-coding rule, kiểm ở CP5)

---

## 10. Nếu có thêm 1 tuần *(slide 6)*

| Ưu tiên | Việc | Trỏ về |
|---|---|---|
| 1 | Bắt selection thật bằng chuột (custom component) | Giới hạn F3.3 — phản hồi hay gặp nhất khi test |
| 2 | Vision model cho trang toàn hình/công thức ảnh | Case abstain lớp ① — hiện đang từ chối, chưa giải |
| 3 | Ôn lại theo lịch (spaced repetition) trên các câu đã sai | Kết quả F2.4 hiện dùng một lần rồi bỏ |
| 4 | Sửa outline bằng tay khi dò chương/mục lệch | F3.4 bậc `heuristic` sai trên slide lạ font |
| 5 | Nhiều tài liệu cùng lúc (ôn cả khoá, không chỉ một buổi) | Job thật của học viên rộng hơn một buổi |

---

## 11. Ánh xạ tính năng → spec & rubric

| Khối rubric | Điểm | Lấy từ đâu trong tài liệu này |
|---|---|---|
| R2 · Lát cắt & thiết kế (`spec.md §4`) | 15 | §1 lát cắt · §6 automation · §7 non-goals |
| R3 · Chỗ khó & kịch bản (`spec.md §5-§6`) | 11 | §8 bốn đường đi · `ARCHITECTURE.md §14` (12 kịch bản, đủ ≥2/lớp) |
| R4 · Kiểm thử (`spec.md §7` + `eval/`) | 15 | tiêu chí nghiệm thu từng tính năng ở §3-§5 → dòng golden set · F4.3 |
| R5 · Prototype chạy được | 8 | §9 definition of done · các mốc trong bảng §2 |
| R6 · Validation | 8 | F2.6 feedback trong flow → `validation/` |

**Ba mục cần điền bằng số sau lượt đo đầu ở CP3** (đừng đoán trước): quality bar % · ngưỡng "nguồn quá mỏng" (số từ) · số câu tối đa sinh được trên 100 từ nguồn.
