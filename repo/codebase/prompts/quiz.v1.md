<!-- TODO(CP3): viết nội dung thật. Item schema + luật chống câu hỏi rác:
     ARCHITECHTURE.md §10. Đổi nội dung => tạo quiz.v2.md, không sửa tại chỗ.
     File này dùng cho CẢ vòng repair qua biến {{repair_feedback}}. -->

# SYSTEM

<!-- Ràng buộc cứng:
     · Chỉ dùng văn bản được cấp; mỗi câu kèm quote nguyên văn suy ra được đáp án.
     · Đúng MỘT đáp án đúng. Nhiễu phải SAI KIỂM CHỨNG ĐƯỢC theo nguồn,
       không phải "cũng có thể đúng".
     · 4 phương án cùng loại, độ dài xấp xỉ (chênh <=2.5x). Không có
       "tất cả đều đúng" / "không đáp án nào đúng".
     · Không hỏi về hình thức tài liệu ("trang này có mấy bullet", "tiêu đề slide là gì").
     · stem không được chứa nguyên văn câu trả lời.
     · Giữ nguyên thuật ngữ như trong slide (kể cả tiếng Anh).
     · Nguồn mỏng => tạo ít câu hơn và nói rõ, KHÔNG nhồi câu trùng ý. -->

# USER

## Văn bản nguồn

{{source_text}}

## Yêu cầu

- Phạm vi: {{scope_label}}
- Số câu: {{n_items}} (đã tính dư 2 để bù item bị loại)
- Cơ cấu độ khó: {{difficulty_mix}}
- Trang có trong phạm vi: {{page_list}}

## Sửa lỗi lượt trước (bỏ trống nếu là lượt sinh đầu)

{{repair_feedback}}
