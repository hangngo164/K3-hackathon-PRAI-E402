"""Bộ exception dùng chung — mỗi lớp chỗ khó một loại lỗi riêng.

Lý do tách: UI phải nói khác nhau cho từng lớp (ARCHITECHTURE.md §14 và FEATURE.md §8).
Bắt được `ScopeTooThin` thì hỏi lại; bắt được `NoGroundedSource` thì abstain và nói lý do.

File lá: KHÔNG import module nào khác trong core/.
"""

from __future__ import annotations


class AppError(Exception):
    """Gốc của mọi lỗi có thông điệp dành cho người dùng."""

    user_message: str = "Có lỗi xảy ra."

    def __init__(self, message: str = "", *, user_message: str = ""):
        super().__init__(message or user_message or self.user_message)
        if user_message:
            self.user_message = user_message
        elif message:
            self.user_message = message


# --- Nạp / chuẩn hoá tài liệu ---
class IngestError(AppError):
    """File không đọc được: sai định dạng, hỏng, có mật khẩu."""


class ConvertError(IngestError):
    """PPTX → PDF thất bại (thiếu LibreOffice, file lạ)."""


# --- Lớp ① Nguồn sự thật ---
class NoGroundedSource(AppError):
    """Scope không đủ căn cứ để trả lời — phải abstain, không được đoán.

    Ví dụ: trang chỉ có sơ đồ, layer text gần trống.
    """


# --- Lớp ② Mơ hồ / thiếu thông tin ---
class ScopeTooThin(AppError):
    """Đoạn bôi đen quá ngắn cho yêu cầu — phải hỏi lại thay vì làm liều."""


# --- Lớp ③ Ngoài phạm vi ---
class OutOfScope(AppError):
    """Người dùng đòi việc feature không được phép làm."""


# --- Tầng LLM ---
class LLMError(AppError):
    """Gọi model thất bại sau khi đã retry."""


class SchemaError(LLMError):
    """Model trả JSON không đúng schema sau vòng repair."""


# --- Verifier ---
class VerifyFailed(AppError):
    """Output không qua kiểm trích dẫn / luật quiz — loại bỏ, không hiển thị."""


# --- Chặn chi phí ---
class BudgetExceeded(AppError):
    """Job vượt MAX_JOB_CALLS hoặc trần token — dừng và báo trước cho người dùng."""
