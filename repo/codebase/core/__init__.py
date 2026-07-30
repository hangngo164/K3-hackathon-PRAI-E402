"""Core logic — thuần Python, KHÔNG import streamlit.

Luật phụ thuộc (ARCHITECHTURE.md §3): ui/ được import core/; core/ không biết đến UI.
Nhờ vậy eval/run.py chạy được toàn bộ pipeline từ dòng lệnh.

Các module sẽ vào đây (theo ARCHITECHTURE.md §16):
    config.py  models.py  cache.py  log.py  llm.py
    convert.py ingest.py  outline.py render.py
    scope.py   summarize.py quiz.py  verify.py
"""
