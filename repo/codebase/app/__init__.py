"""Tầng UI Streamlit — chỉ layout + `session_state`, không chứa logic nghiệp vụ.

    main.py          entrypoint:  streamlit run app/main.py — hai UI state
    state.py         khoá session_state + get/set (theo từng tài liệu)
    sidebar.py       nạp nhiều file · chọn file đang đọc · mục lục · chi phí
    chat.py          cửa sổ chat: nơi DUY NHẤT người dùng ra yêu cầu
    viewer.py        Normal Mode — ảnh trang + điều hướng
    panel_quiz.py    Quiz Mode — bảng làm bài + chấm + giải thích
    panel_summary.py renderer cho bubble tóm tắt trong chat

Luật phụ thuộc: `app/` import `tools/` và `agent_core/`; không chiều nào ngược lại.
Nhờ vậy `eval/run.py` chạy được toàn bộ pipeline từ dòng lệnh, không cần Streamlit.

Không eager-import submodule ở đây: `main.py` import thẳng cái nó cần.
"""
