# AI SPEC — Trợ lý Ôn Slide · Nhóm [XX] · Zone [X]

Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [ ] Tối ưu tính năng có sẵn  [x] Tính năng mới

## §1. User & Job

- Job executor + workflow: sinh viên nạp nhiều file slide/PDF, chọn tài liệu muốn ôn, rồi dùng 3 thao tác chính trên đúng tài liệu đó: tóm tắt theo đoạn/trang/mục/chương/toàn bộ, sinh quiz có neo nguồn theo trang, và hỏi đáp tự do nhưng chỉ trả lời khi tìm được căn cứ trong tài liệu.
- Core JTBD (không tên sản phẩm/AI trong câu): học viên cần đọc nhanh tài liệu dài, kiểm tra lại phần chưa hiểu, và ôn tập ngay sau buổi học mà không phải tự lọc thủ công từng trang.
- Problem statement (không dùng chữ AI): tài liệu slide dài, nhiều trang chỉ có ý chính hoặc hình, nên người học khó biết phải ôn phần nào trước, khó tự tạo câu hỏi ôn tập, và cũng khó hỏi lại mà không bị trả lời lan man.
- Evidence:

  - Evidence:
    - Đã phân tích 2.522 dòng chatlog ẩn danh. Golden set có 30 case, gồm
      13 case thường, 13 case rủi ro và 4 case hiếm. Trong đó có 10 case
      phát triển trực tiếp từ lời người học thật.
    - Ví dụ nguyên văn:
      - “tóm tắt nội dung chính trong slide này” — chatlog C0001/T0649/M1149
      - “giải thích 4 chiến lược” — chatlog C0002/T0959/M1109
      - “tạo quiz để tôi hiểu rõ và ôn lại slide này” — chatlog C0063/T0849/M0003
      - “tóm tắt hết slide trong vài câu đi” — chatlog C0020/T0122/M2504
      - “Tại sao câu này tôi lại chọn sai, hãy giải thích” — chatlog C0023/T0399/M1331

## §2. Impact & quyết định chọn

- Bảng impact của ít nhất 3 ứng viên:
  - Ôn toàn bộ tài liệu: tác động lớn nhất, vì gần như ai cũng phải làm; tần suất cao; tốn nhiều thời gian; khả thi vừa phải.
  - Sinh quiz theo tài liệu: giúp chuyển từ đọc thụ động sang tự kiểm tra; dùng hằng ngày; tiết kiệm thời gian tự ra đề; khả thi cao vì đầu ra rõ.
- Ứng viên đã loại và lý do: tự động làm bài thay sinh viên bị loại vì cost-of-error cao, dễ vượt mục tiêu học tập và khó kiểm soát chất lượng.
- Ứng viên được chọn và lý do bằng số: chọn 3 luồng trên vì đều gắn trực tiếp với nhu cầu ôn tập sau học; có thể kiểm chứng bằng golden set 30 case; mỗi luồng đều có hành vi đầu ra rõ để đo được.

## §3. Giải pháp tương tự đã nghiên cứu

- Sản phẩm 1 — flow / đáng học / đáng né / điểm khác biệt: các công cụ chat tài liệu kiểu hỏi-đáp nhanh rất tiện, nhưng nếu không neo nguồn thì dễ bịa; mình học cách truy hồi theo đoạn và né kiểu trả lời chung chung.
- Sản phẩm 2 — flow / đáng học / đáng né / điểm khác biệt: công cụ tạo quiz từ tài liệu giúp học viên tự kiểm tra nhanh, nhưng thường nhồi quá nhiều câu hoặc hỏi ngoài phạm vi; sản phẩm của mình chặn câu rác bằng code và bắt neo trang cho từng câu.

## §4. Thiết kế

- Lát cắt một câu (1 user · 1 việc · 1 quyết định AI · 1 kết quả): một sinh viên nạp slide, bôi chọn nội dung hoặc yêu cầu theo trang, hệ thống quyết định tóm tắt/ra quiz/trả lời dựa trên đúng phạm vi đó, và trả về output có neo nguồn `[trang N]`.
- Non-goals (ít nhất 3):
  - Không tự học kiến thức ngoài tài liệu đã nạp.
  - Không làm chatbot tổng quát cho mọi chủ đề.
  - Không tự chấm điểm theo cảm tính nếu thiếu căn cứ trong nguồn.
- Mức prototype: [ ] Sketch [ ] Mock [x] Working
- Phần mock/phần thật: phần upload, chọn tài liệu, viewer, chat, quiz panel, kiểm neo nguồn và log trace là thật; các hành vi sinh nội dung phụ thuộc model nhưng bị ràng bằng `verify.py`.
- Automation: [ ] Augment [x] Conditional [ ] Automate
- Lý do theo cost-of-error: câu tóm tắt/quiz/chchat chỉ được tự động trả lời khi đủ căn cứ và neo nguồn; nếu thiếu căn cứ thì phải từ chối hoặc hỏi lại vì sai một câu có thể làm người học ôn sai kiến thức.

### §4b. Nguyên tắc HAX/PAIR

| Nguyên tắc           | Áp dụng cụ thể trong prototype                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
| G1                     | Người dùng luôn giữ quyền chọn tài liệu và chọn thao tác, model không tự quyết định hành động. |
| G10                    | Mọi output phải neo được về trang/khối nguồn; câu nào không neo được thì bị loại.                 |
| G11                    | Hệ thống nói rõ số lượng thực tế tạo được, không im lặng giảm output khi lọc lỗi.                |
| Tách kiểm bằng code | `agent_core/verify.py` chặn quote bịa, câu hỏi rác, và trích dẫn ngoài phạm vi.                        |

## §5. Kiểu lỗi — 4 lớp chỗ khó và kịch bản

| ID  | Lớp                         | Input/tình huống                                              | Rủi ro                                              | Hành vi mong muốn                                  | Cách kiểm tra                    |
| --- | ---------------------------- | --------------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- | ---------------------------------- |
| R01 | ① Nguồn sự thật          | Tóm tắt trang chỉ có sơ đồ                               | Không đọc được chữ nhưng vẫn bịa ra bullet | Từ chối, nói rõ trang chủ yếu là hình        | `scope.resolve` + `verify`     |
| R02 | ① Nguồn sự thật          | Quiz có số liệu/tỷ lệ trong nguồn                         | Model sinh số không có trong slide                | Mọi số trong output phải xuất hiện trong nguồn | `check_numbers`                  |
| R03 | ② Mơ hồ/thiếu thông tin | Người dùng nói “đoạn này”, “phần đó”              | Không rõ scope thật là gì                       | Hỏi lại hoặc dùng ngữ cảnh trước nếu đủ   | `route` + state                  |
| R04 | ② Mơ hồ/thiếu thông tin | Yêu cầu tóm tắt chương không tồn tại                   | Route sai thành exception hoặc đoán đại        | Hỏi lại bằng các lựa chọn có thật            | `intent._resolve_unit`           |
| R05 | ③ Ngoài phạm vi           | Hỏi đề thi sẽ hỏi gì, hoặc hỏi kiến thức ngoài slide | Model suy diễn kiến thức nền                     | Từ chối và chỉ nói trong phạm vi tài liệu    | prompt system +`ask`             |
| R06 | ③ Ngoài phạm vi           | Giải hộ bài tập thay vì hỗ trợ ôn tập                  | Bị biến thành giải bài thay học                | Từ chối ngắn, gợi ý tạo quiz để tự kiểm    | prompt system                      |
| R07 | ④ Đặc thù domain         | Slide song ngữ hoặc thuật ngữ chuyên ngành                | Dịch sai, làm lệch nghĩa học thuật             | Giữ nguyên thuật ngữ đúng trong tài liệu     | `verify` + prompt                |
| R08 | ④ Đặc thù domain         | Công thức/bảng số liệu trên slide                         | Sai công thức, sai thứ tự bảng                  | Copy đúng hoặc nói không đọc được          | `check_quote`, `check_numbers` |

## §6. Bốn đường đi của trải nghiệm

- Happy path: sinh viên chọn slide/chapter/page, bấm tóm tắt hoặc quiz, hệ thống trả output có neo `[trang N]` và có thể bấm quay lại đúng vị trí.
- Low-confidence: khi trang quá nhiều hình hoặc dữ kiện chưa đủ, hệ thống hạ confidence và nói rõ phần nào không chắc.
- Failure/không có căn cứ: nếu không tìm được đoạn phù hợp hoặc quote không khớp, hệ thống loại output thay vì bịa.
- Correction — người dùng sửa: người dùng có thể sửa lại phạm vi, ví dụ đổi từ “đoạn này” sang “trang 6” hoặc chọn đúng chương.
- Khi bị yêu cầu ngoài phạm vi: hệ thống từ chối gọn và mời người dùng đặt câu hỏi trong phạm vi slide đã nạp.

## §7. Kiểm thử

- Các chiều chất lượng và định nghĩa kiểm chứng được:
  - Tóm tắt: có đủ ý chính, có neo trang hợp lệ, không bịa quote.
  - Quiz: đúng loại câu, đủ phương án, không lộ đáp án, không có số bịa.
  - Chat: chỉ trả lời từ đoạn tìm được, không gọi model khi không có căn cứ.
  - Rủi ro: abstain đúng khi trang quá ít chữ hoặc hỏi ngoài phạm vi.
- Golden set: `eval/golden-set.csv`
- Quality bar chốt trước 23:59 ngày 1: Đạt khi ≥ 90% case qua bộ, và không có case ①/③ bị trả lời bịa.
- Kết quả các lượt chạy: `eval/results.md`

## §8. Phân công & kế hoạch

Phân công chính: 

* Nguyễn Huy Hoàng:  prompt, schema, provider, verifier và retriaval
* Nguyễn Thị Hoàng Yến: pipeline đọc tài liệu, outline, scope, UI.
* Quách Xuân Trường: router, intent, ba tools, cache và logging.
* Ngô Thị Hằng: spec, validation và demo.

- Ít nhất 3 willing users:
- Kế hoạch validation CP5: cho 3 người dùng thử 3 câu hỏi cố định gồm tóm tắt, quiz, và hỏi đáp; ghi lại câu nào bị từ chối, câu nào trả lời đúng căn cứ, rồi đối chiếu với golden set.
- Multi-prototype (nếu có): hiện chốt một prototype chính, chưa tách nhiều phương án.

## §9. Changelog

| Thời điểm | Thay đổi                                                                             | Lý do/feedback/case liên quan                                  |
| ------------ | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 2026-07-30   | Chốt luồng`summarize`/`quiz`/`ask`, neo nguồn theo trang và kiểm bằng code | Bám đúng cách prototype đang chạy trong`repo/codebase/`  |
| 2026-07-30   | Bổ sung case rủi ro ①-④ cho golden set                                             | Phản ánh các lỗi thực tế trong`repo/eval/golden-set.csv` |
