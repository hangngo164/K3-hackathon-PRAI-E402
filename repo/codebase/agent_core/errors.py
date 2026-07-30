"""Bộ exception dùng chung — mỗi lớp chỗ khó một loại lỗi riêng.

Lý do tách: UI phải nói khác nhau cho từng lớp. Bắt được `NoGroundedSource` thì
abstain và nói lý do; bắt được `OutOfScope` thì từ chối gọn kèm việc làm được.

Lớp ② (mơ hồ / thiếu thông tin) KHÔNG có exception riêng ở đây: nó xảy ra khi
điều phối, trước lúc bất kỳ tool nào chạy, nên `agent_core/intent.py` xử bằng
cách trả `Plan(kind="clarify")` — một câu hỏi lại kèm lựa chọn có thật. Dùng
exception cho nó sẽ bắt `app/` phải bắt lỗi để hỏi một câu hoàn toàn bình thường.

File lá: KHÔNG import module nào khác trong `agent_core/`.
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


# --- Lớp ③ Ngoài phạm vi ---
class OutOfScope(AppError):
    """Người dùng đòi việc feature không được phép làm."""


# --- Tầng LLM ---
class LLMError(AppError):
    """Gọi model thất bại sau khi đã retry."""


class TransientLLMError(LLMError):
    """Lỗi ĐÁNG retry: 429, 5xx, timeout, đứt mạng.

    Tách khỏi LLMError để tầng retry biết cái gì thử lại được. Retry mù một lỗi
    "sai API key" chỉ tốn 3 lần chờ rồi vẫn hỏng, mà người dùng phải ngồi đợi.
    """


class SchemaError(LLMError):
    """Model trả JSON không đúng schema sau vòng repair."""


# --- Verifier ---
class VerifyFailed(AppError):
    """Output không qua kiểm trích dẫn / luật quiz — loại bỏ, không hiển thị."""


# --- Chặn chi phí ---
class BudgetExceeded(AppError):
    """Job vượt MAX_JOB_CALLS hoặc trần token — dừng và báo trước cho người dùng."""
