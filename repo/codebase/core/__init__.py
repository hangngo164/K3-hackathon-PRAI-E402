"""Core logic — thuần Python, KHÔNG import streamlit.

Luật phụ thuộc (STRUCTURE.md §4): ui/ được import core/; core/ không biết đến UI.
Nhờ vậy eval/run.py chạy được toàn bộ pipeline từ dòng lệnh.

Không eager-import submodule ở đây: mỗi module tự khai phụ thuộc của nó, và
eval/run.py không phải nạp cả lớp UI-facing chỉ để chạy một scope.
"""
