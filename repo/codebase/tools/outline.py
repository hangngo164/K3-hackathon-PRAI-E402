"""Bậc 3 của thang dò chương/mục: nhờ model gom các trang thành chương.

Tồn tại như một tool riêng, không nằm trong `agent_core/outline.py`, để giữ
luật phụ thuộc một chiều: `agent_core/` không bao giờ import `providers/`.
`agent_core.outline.build_outline()` nhận hàm này qua tham số `grouper`.

Đầu vào CHỈ là danh sách tiêu đề trang — không đưa toàn văn tài liệu vào prompt.
Một deck 40 trang có ~40 dòng tiêu đề: một lời gọi rẻ, thay vì đọc cả tài liệu
để làm một việc thuần cấu trúc.

Bậc này chỉ chạy khi bậc `toc` và `heuristic` đều trượt, nên với phần lớn slide
nó không tốn lời gọi nào.
"""

from __future__ import annotations

from agent_core.log import trace
from agent_core.schemas import OUTLINE_SCHEMA

PROMPT_ID = "outline"


def group_pages(page_title_lines: list[str], total_pages: int) -> list[dict] | None:
    """Trả list chapter thô (chưa kiểm) hoặc None.

    Không ném exception ra ngoài: dò chương/mục hỏng thì thang tụt về 'flat' và
    người dùng vẫn nạp được file, vẫn tóm tắt được theo trang. Làm chết bước
    nạp file vì một tính năng phụ là đánh đổi sai.
    """
    if not page_title_lines:
        return None

    import providers  # import muộn: agent_core gọi hàm này cả khi chưa có API key

    try:
        result = providers.complete_json(
            PROMPT_ID,
            {
                "page_titles": "\n".join(page_title_lines),
                "total_pages": str(total_pages),
            },
            OUTLINE_SCHEMA,
            "outline",
            tier="fast",
            temperature=0.0,  # việc thuần cấu trúc: cùng đầu vào phải ra cùng kết quả
        )
    except Exception as exc:
        trace("verify_fail", stage="outline", error=str(exc)[:200])
        return None

    chapters = result.data.get("chapters")
    return chapters if isinstance(chapters, list) and chapters else None
