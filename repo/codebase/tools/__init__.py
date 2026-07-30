"""Tầng nghiệp vụ — mỗi file một việc mà người dùng bấm được.

    summarize.py  tóm tắt một phạm vi (5 tầng: đoạn/trang/mục/chương/tài liệu)
    quiz.py       sinh câu hỏi ôn tập, có vòng kiểm-sửa
    ask.py        chat hỏi đáp tự do trên cả tài liệu
    outline.py    bậc 3 của thang dò chương/mục (hàm gom, cấp cho agent_core)
    registry.py   khai báo 3 tool trên cho UI và eval dùng chung

Luật của tầng này:
  · gọi được `agent_core/` và `providers/`, KHÔNG import `app/`
  · không tự cắt văn bản (việc của `agent_core/scope.py`)
  · không tự kiểm trích dẫn (việc của `agent_core/verify.py`)
  · không bao giờ trả thẳng output của model ra UI — mọi thứ đi qua verify trước

Không eager-import ở đây: `eval/run.py` chỉ cần một tool thì không phải nạp cả ba.
"""
