"""agent-core — logic thuần Python. KHÔNG import streamlit, KHÔNG import providers.

    config · errors · models · cache          nền
    ingest · convert                          file slide -> Document + ảnh trang
    outline                                   dò chương/mục (bậc LLM nhận qua tham số)
    intent                                    route model đề xuất -> Plan chạy được
    scope                                     phạm vi -> văn bản + chiến lược gọi
    retrieve                                  tìm đoạn cho chat (BM25, không embedding)
    prompting · schemas                       hợp đồng với model
    verify · log                              kiểm bằng code + ghi trace

Luật phụ thuộc (một chiều, không ngoại lệ):

    app/  ->  tools/  ->  providers/  ->  agent_core/

`agent_core` là đáy: nó không biết đang chạy provider nào, cũng không biết có UI
hay không. Hai chỗ từng muốn phá luật này, cả hai giải bằng cách tách phần cần
model lên `tools/`:

    outline.py  bậc 3 nhận hàm `grouper` qua tham số  -> tools/outline.py
    intent.py   nhận `Route` model đã trả về          -> tools/router.py

Nhờ luật đó, `eval/run.py` chạy được toàn bộ pipeline từ dòng lệnh.

Không eager-import submodule ở đây: mỗi module tự khai phụ thuộc của nó.
"""
