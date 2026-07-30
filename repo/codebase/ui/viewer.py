"""Viewer: ảnh trang + overlay vàng + block picker + điều hướng.

TODO(CP2). Thiết kế "bôi đen" hai tầng: ARCHITECHTURE.md §7.
Không gọi AI.

Tầng 1 (bắt buộc, không cần JS): checkbox theo khối văn bản => vẽ overlay vàng
lên đúng bbox trên ảnh trang. Anchor thu được GIỐNG HỆT thứ selection thật cho,
nên nâng cấp Tầng 2 (custom component bắt getSelection) không phải sửa core/.

Dùng @st.fragment cho khối này để lật trang / tick khối không kéo cả trang rerun.
"""

from __future__ import annotations


def render() -> None:
    """F3.2 hiển thị slide + F3.3 bôi đen. Trả về qua session_state, không return."""
    raise NotImplementedError("TODO(CP2)")


def goto(page_no: int, block_ids: list[str] | None = None) -> None:
    """Nhảy tới nguồn (F2.5) — dùng bởi nút "xem chỗ này" trên bullet/câu hỏi."""
    raise NotImplementedError("TODO(CP2)")
