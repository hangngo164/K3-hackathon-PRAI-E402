"""Sinh bản tóm tắt cho một scope, gộp map-reduce nhiều tầng.

TODO(CP3) selection + page · TODO(CP4) các tầng trên.
Hợp đồng output + 5 ràng buộc prompt: ARCHITECHTURE.md §9.
Không tự cắt văn bản (việc của scope.py), không tự kiểm trích dẫn (việc của verify.py).

Mức tự động hoá: AUTOMATE — vì mỗi bullet có neo nguồn, người dùng bấm
"xem chỗ này" là kiểm được ngay, sai thì sửa rẻ.
"""

from __future__ import annotations

from .models import Document, Scope


def summarize(
    doc: Document,
    scope: Scope,
    target_id: str | None = None,
    selection_block_ids: list[str] | None = None,
) -> dict:
    """Trả payload theo SUMMARY_SCHEMA, đã qua verify.

    Cache hit (cùng nội dung + prompt_version + model) thì trả luôn, không gọi model.
    """
    raise NotImplementedError("TODO(CP3)")


def summarize_pages(doc: Document, page_nos: list[int]) -> dict[int, dict]:
    """Tầng dưới của map-reduce — chạy song song ThreadPoolExecutor(max_workers=4).

    Không được gọi st.* trong thread; thread chỉ trả dữ liệu về.
    """
    raise NotImplementedError("TODO(CP4)")


def reduce_summaries(children: list[dict], scope: Scope, label: str) -> dict:
    """Gộp tóm tắt tầng dưới thành tóm tắt tầng trên.

    Neo trang phải truy về TRANG GỐC, không neo về "tóm tắt của tóm tắt".
    """
    raise NotImplementedError("TODO(CP4)")
