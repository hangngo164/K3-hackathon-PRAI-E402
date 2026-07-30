# Kết quả evaluation

## Quy tắc chấm

- Một case chỉ đạt khi thỏa toàn bộ `expected_behavior` trong `golden-set.csv`.
- Thiếu output hoặc trace để kiểm một điều kiện được tính là **chưa đạt**, không suy đoán từ prompt.
- Case lớp ① hoặc ③ có thông tin không neo được vào nguồn là fail cứng.
- Kết quả unit test chỉ là bằng chứng cho guardrail bằng code, không thay thế tỷ lệ golden set.

## Quality bar

Đạt khi ≥ 90% case qua bộ, và không có case lớp ① hoặc ③ bị trả lời bịa hay vượt phạm vi.

## Các lượt chạy

| Lượt   | Thời điểm | Số case đạt | Tổng case | Tỷ lệ | So với quality bar                                                                           | Bằng chứng                                    |
| -------- | ------------ | -------------: | ---------: | ------: | --------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Baseline | 2026-07-30   |              9 |         30 |   30,0% | Chưa đạt; cần thêm 18 case đạt, tương đương 60 điểm phần trăm, để chạm 90% | `traces/2026-07-30.jsonl`, code và unit test |

Kiểm tra hồi quy code chạy bằng `.venv\Scripts\python.exe -m pytest -q`: **137/137 test đạt trong 0,41 giây**. Con số này không được cộng vào 9/30 golden case.

## Kết quả từng case

| Case | Input rút gọn                    | Output/bằng chứng quan sát                                                                                              | Kết quả   |
| ---- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------- |
| G001 | Tóm tắt trang chỉ có hình     | `scope.resolve` từ chối trang không đủ chữ; test `test_image_only_page_abstains` đạt                           | Đạt       |
| G002 | Quiz có số liệu                 | `check_numbers` chỉ tạo warning, trong khi tiêu chí yêu cầu fail item nếu số không có trong nguồn             | Chưa đạt |
| G003 | Tóm tắt có quote bịa           | Trace có`verify_fail stage=summary`; bullet sai bị loại và `_meta.dropped_bullets` ghi số lượng                 | Đạt       |
| G005 | Xin 15 câu từ một trang         | Code sinh dư, dedupe, cắt theo số có căn cứ và`_shortfall_warning` báo số thực tế                             | Đạt       |
| G007 | Giải hộ bài tập                | Prompt quy định`out_of_scope`, nhưng trace không lưu final payload để xác nhận câu trả lời thực tế         | Chưa đạt |
| G008 | Đoán nội dung đề thi          | Có luật từ chối trong prompt, chưa có output gắn case để kiểm model có tuân thủ                               | Chưa đạt |
| G009 | So sánh GPT-5 ngoài slide        | Có luật chỉ dùng excerpt, chưa có final answer gắn case                                                             | Chưa đạt |
| G010 | Hai phương án cùng đúng      | Verifier chỉ bắt phương án trùng chuỗi; chưa phát hiện hai câu khác chữ nhưng cùng đúng về nghĩa        | Chưa đạt |
| G011 | Giữ thuật ngữ EN                | Prompt yêu cầu giữ thuật ngữ, chưa có output gắn case để chấm                                                   | Chưa đạt |
| G012 | Công thức softmax                | Quote được kiểm nhưng phần diễn giải công thức và số mới chỉ cảnh báo; chưa bảo đảm copy nguyên dạng | Chưa đạt |
| G013 | Độ dài phương án             | Code bắt tỷ lệ >2,5x, nhưng chưa kiểm điều kiện cấp bộ “đáp án đúng không luôn dài nhất”             | Chưa đạt |
| G014 | “tóm tắt nội dung chính...”  | Đã có input thật và tiêu chí; tài liệu tương ứng không có trong repo để chạy lại output                  | Chưa đạt |
| G015 | “giải thích 4 chiến lược”   | Đã có input thật và ngữ cảnh chọn; chưa có output lưu theo case                                                 | Chưa đạt |
| G016 | Yêu cầu quiz viết hoa           | Đã có input thật; chưa có lượt chạy gắn`case_id`                                                               | Chưa đạt |
| G017 | Giải thích đoạn bôi đen      | Viewer hỗ trợ anchor, nhưng chưa có output/click trace cho đúng case                                                | Chưa đạt |
| G018 | Tóm tắt toàn bộ slide          | Map-reduce đã triển khai; chưa có bảng phủ chương của output gắn case                                           | Chưa đạt |
| G019 | “bộ quizz liên quan”           | Quiz có verifier; chưa có output thực tế gắn case                                                                    | Chưa đạt |
| G020 | “tóm tắt hết slice...”        | Input thật có typo; chưa có route/output gắn case                                                                     | Chưa đạt |
| G021 | “cách xử lý ngữ cảnh”       | Input thật rất cụt; chưa có output để xác nhận dùng selection hay hỏi lại đúng                               | Chưa đạt |
| G022 | “Designt Pattern ReAct...”       | Input thật trộn EN-VI và typo; chưa có output gắn case                                                               | Chưa đạt |
| G023 | “Giải thích biều đồ đc...” | Code không OCR ảnh và có đường từ chối trang hình; chưa chạy đúng case trên file nguồn                     | Chưa đạt |
| G024 | Slide song ngữ                    | Prompt yêu cầu giữ nguyên ngôn ngữ; chưa có output gắn case                                                       | Chưa đạt |
| G025 | Bảng số liệu                    | Text extraction chưa phục hồi cấu trúc bảng;`check_numbers` không chặn cứng nên có thể lệch hàng/cột      | Chưa đạt |
| G026 | Mất mạng giữa map-reduce        | Lỗi từng trang được giữ cục bộ, nhưng lỗi ở bước reduce cuối chưa bảo đảm trả phần đã sinh           | Chưa đạt |
| G027 | Tóm tắt trang 6                  | Trace cuối route đúng`summarize/page/6`; test route giữ target trang đạt                                           | Đạt       |
| G028 | Tóm tắt chương 99              | Trace trả`clarify`, không chạy tool; test option chỉ lấy đơn vị có thật đạt                                  | Đạt       |
| G029 | So sánh hai chương              | Trace trả`clarify`, không âm thầm chạy một chương                                                                | Đạt       |
| G030 | “Tóm tắt đoạn này”          | Hai lượt trace ổn định cuối đều trả`clarify`, không tự đoán selection                                       | Đạt       |
| G031 | “Tạo quiz từ phần đó”       | Ba lượt trace route đúng`quiz/chapter/ch02`; test last scope đạt                                                   | Đạt       |
| G032 | “Tại sao câu 5 sai?”           | Trace route thành`explain`; code lấy explanation đã verify, không gọi model lại                                   | Đạt       |

## Phân tích khoảng cách

| Nhóm lỗi                          | Case                         | Nguyên nhân                                                                              | Hướng xử lý ưu tiên                                                                            |
| ----------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Guardrail chưa đủ chặt          | G002, G010, G012, G013, G025 | Một số luật mới ở prompt/warning hoặc không kiểm được ngữ nghĩa               | Chặn số không có nguồn; thêm kiểm cấp bộ; dùng bước review ngữ nghĩa có rubric riêng |
| Thiếu output phúc khảo được   | G007-G009, G011, G014-G024   | Trace hiện ghi route/LLM call/verify fail nhưng không gắn`case_id` và final payload | Viết`eval/run.py` lưu `case_id`, output rút gọn, model, prompt version và pass/fail         |
| Failure recovery chưa hoàn chỉnh | G026                         | Lỗi reduce cuối có thể làm mất kết quả map đã có                                | Lưu checkpoint từng trang và cho phép trả bản tóm tắt một phần                             |

## Kết luận

Lượt baseline **chưa đạt quality bar**. Kết quả 30,0% chủ yếu phản ánh thiếu bằng chứng output theo từng case, không mâu thuẫn với việc 137 unit test đều đạt. Failure cần sửa trước là `G002`: tiêu chí yêu cầu số ngoài nguồn làm fail item nhưng code hiện chỉ cảnh báo.
