<!-- TODO(CP3): viết nội dung thật. Hợp đồng output: ARCHITECHTURE.md §9.
     Đổi nội dung file này => tạo summarize.v2.md, KHÔNG sửa tại chỗ,
     và ghi changelog spec.md §9. Kết quả eval luôn gắn với version prompt. -->

# SYSTEM

<!-- 5 ràng buộc cứng, viết thành chỉ dẫn cho model:
     1. Chỉ dùng văn bản được cấp. Không thêm kiến thức ngoài, kể cả khi biết rõ.
     2. Mỗi bullet kèm quote copy NGUYÊN VĂN từ nguồn (không sửa chữ, không dịch).
     3. Giữ nguyên thuật ngữ như trong slide (kể cả tiếng Anh) — không "dịch giúp".
     4. Số liệu/công thức: copy đúng, không làm tròn, không diễn giải lại.
     5. Nguồn < ~40 từ hữu ích => confidence "low", bullets rỗng, nêu lý do trong not_covered.
     Ranh giới: từ chối gọn nếu bị đòi việc ngoài phạm vi (lớp ③). -->

# USER

<!-- Thứ tự khối phải giữ đúng như dưới đây — phần bất biến ĐẶT TRƯỚC để
     prompt caching của OpenAI ăn theo tiền tố (ARCHITECHTURE.md §12). -->

## Văn bản nguồn

{{source_text}}

## Ngữ cảnh xung quanh (chỉ để hiểu, KHÔNG tóm tắt vào)

{{context_text}}

## Yêu cầu

- Phạm vi: {{scope_label}}
- Số bullet: {{n_bullets_min}}-{{n_bullets_max}}
- Trang có trong phạm vi: {{page_list}}
