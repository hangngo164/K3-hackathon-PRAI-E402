"""Chat hỏi đáp tự do trên cả tài liệu.

Khác tóm tắt và quiz ở đúng một chỗ, nhưng là chỗ quyết định: người dùng gõ câu
hỏi tự do nên KHÔNG có phạm vi cho sẵn. Hệ quả dây chuyền:

  · phải tự tìm đoạn liên quan  → `agent_core/retrieve.py`
  · "trích dẫn hợp lệ" nghĩa là nằm trong ĐOẠN ĐÃ TÌM, không phải trong một
    scope người dùng chọn  → `verify.check_citation` thay vì `check_anchor`
  · model phải được phép nói "không có trong tài liệu" → `answerable=false`

Ba đường thoát, không đường nào là đoán:
    not_in_document  tài liệu không nói về chuyện này
    out_of_scope     đòi việc ngoài phạm vi ôn slide (giải bài hộ, hỏi kiến thức ngoài)
    too_vague        câu hỏi chưa đủ rõ để tìm

Không tìm được đoạn nào thì TỪ CHỐI NGAY, không gọi model: gọi cũng chỉ để nghe
model nói "tôi không biết", mà vẫn mất tiền và mất mấy giây chờ.
"""

from __future__ import annotations

from agent_core import cache, prompting, retrieve, verify
from agent_core import scope as scope_lib
from agent_core.config import settings
from agent_core.log import trace
from agent_core.models import Document
from agent_core.schemas import ANSWER_SCHEMA

PROMPT_ID = "ask"
KIND = "answers"
_HISTORY_TURNS = 4  # đủ để hiểu "cái đó là gì", không đủ để lạc khỏi câu hỏi hiện tại


def ask(
    doc: Document,
    question: str,
    history: list[dict] | None = None,
    *,
    scope: str | None = None,
    target_id: str | None = None,
    force: bool = False,
) -> dict:
    """Trả payload theo ANSWER_SCHEMA + `_meta`. Không bao giờ ném vì câu hỏi lạ.

    `history`: [{"role": "user"|"assistant", "content": str}, ...] theo thứ tự thời gian.

    `scope`/`target_id` thu hẹp vùng tìm về đúng một phần tài liệu — dùng cho câu
    hỏi đã tự nêu phạm vi ("giải thích trang 15"). Không truyền thì tìm cả tài liệu
    như cũ.
    """
    question = (question or "").strip()
    if len(question) < 3:
        return _refusal("too_vague", "Câu hỏi ngắn quá — bạn muốn hỏi về phần nào của slide?")

    cfg = settings()
    chunks = _chunks_in_scope(doc, scope, target_id)
    if not chunks:
        trace("verify_fail", stage="chat", reason="empty_scope", scope=scope, target_id=target_id)
        return _refusal(
            "not_in_document",
            "Phần bạn hỏi không có chữ nào đọc được — nhiều khả năng đó là trang hình.",
            followup="Thử hỏi một phần khác, hoặc mở trang đó ra xem trực tiếp.",
        )

    results = retrieve.search(
        chunks, _search_query(question, history), cfg.chat_top_k, cfg.chat_min_score
    )
    if scope and not results:
        # Câu hỏi đã tự nêu phạm vi ("giải thích trang 15") thì phần lớn từ trong
        # câu là từ chỉ vị trí, và BM25 lọc sạch chúng thành không còn từ khoá
        # nào. Khi đó chính PHẠM VI là câu trả lời cho "tìm ở đâu" — trả về cả
        # phạm vi còn đúng hơn là báo không tìm thấy trên một trang có đầy chữ.
        results = [retrieve.ScoredChunk(chunk=c, score=1.0) for c in chunks[:cfg.chat_top_k]]

    if not results:
        trace("verify_fail", stage="chat", reason="no_chunk", question=question)
        return _refusal(
            "not_in_document",
            "Mình không tìm thấy phần nào trong tài liệu này nói về điều đó.",
            followup="Thử hỏi bằng đúng từ ngữ xuất hiện trên slide, hoặc nói rõ trang "
                     "bạn đang nghi — ví dụ \"trang 12 nói gì về loss?\".",
        )

    prompt_text = retrieve.as_prompt_text(results)   # có nhãn trang/khối, gửi model
    source_text = retrieve.as_source_text(results)   # sạch, dùng để verify quote
    allowed = retrieve.allowed_unit_ids(results)
    version = prompting.load(PROMPT_ID).version
    key = cache.content_key(
        verify.normalize(question), source_text, PROMPT_ID, version, cfg.model_for("main")
    )

    if not force:
        cached = cache.load_artifact(doc.doc_hash, KIND, key)
        if cached:
            cached.setdefault("_meta", {})["cached"] = True
            return cached

    payload = _call(question, prompt_text, history)
    payload = _finalize(payload, results, allowed, source_text, version)
    cache.save_artifact(doc.doc_hash, KIND, key, payload)
    return payload


def _chunks_in_scope(doc: Document, scope: str | None, target_id: str | None) -> list:
    """Đoạn được phép trả lời từ. Không có scope ⇒ cả tài liệu, đúng hành vi cũ.

    Lọc theo TRANG chứ không gọi `scope.resolve()`: verify của chat đối chiếu vào
    `allowed_unit_ids` của các đoạn tìm được, nên đường đi phải vẫn là đường của
    `retrieve.py`. Gọi `resolve()` ở đây sẽ tạo ra một loại "phạm vi hợp lệ" thứ
    hai cho cùng một câu trả lời.
    """
    chunks = retrieve.build_chunks(doc)
    if not scope:
        return chunks
    pages = {p.page_no for p in scope_lib.pages_in_scope(doc, scope, target_id)}
    return [c for c in chunks if c.page_no in pages] if pages else []


def _search_query(question: str, history: list[dict] | None) -> str:
    """Câu hỏi nối tiếp ("còn cái kia thì sao?") không có từ khoá nào để tìm.

    Ghép thêm câu hỏi trước của người dùng để BM25 còn chỗ bám. Chỉ câu hỏi
    trước, không phải cả hội thoại: nối dài quá thì chủ đề cũ át chủ đề mới.
    """
    if not history:
        return question
    previous = [t.get("content", "") for t in history if t.get("role") == "user"]
    return f"{question} {previous[-1]}" if previous else question


def _call(question: str, prompt_text: str, history: list[dict] | None) -> dict:
    import providers  # import muộn: `tools.ask` được import cả khi chưa có API key

    result = providers.complete_json(
        PROMPT_ID,
        {
            "source_text": prompt_text,
            "history": _format_history(history),
            "question": question,
        },
        ANSWER_SCHEMA,
        "answer",
        tier="main",
        temperature=0.1,  # hỏi đáp cần ổn định, không cần sáng tạo
    )
    return result.data


def _format_history(history: list[dict] | None) -> str:
    if not history:
        return "(chưa có)"
    recent = [t for t in history if t.get("role") in ("user", "assistant")][-_HISTORY_TURNS:]
    return "\n".join(
        f"{'Người dùng' if turn['role'] == 'user' else 'Trợ lý'}: "
        f"{str(turn.get('content', ''))[:400]}"
        for turn in recent
    ) or "(chưa có)"


def _finalize(payload: dict, results: list, allowed: list[str],
              source_text: str, version: str) -> dict:
    """Kiểm từng trích dẫn; câu trả lời không còn trích dẫn nào thì HẠ xuống từ chối.

    Đây là luật quan trọng nhất của chat: một câu trả lời trôi chảy mà không neo
    được vào slide thì không phân biệt được với một câu bịa. Thà nói không tìm
    thấy còn hơn để người ôn thi tin một câu không kiểm được.
    """
    warnings: list[str] = []
    kept: list[dict] = []

    for citation in payload.get("citations") or []:
        check = verify.check_citation(verify.anchor_from_dict(citation), allowed, source_text)
        if check.passed:
            kept.append(citation)
        else:
            warnings.append("; ".join(check.reasons))
            trace("verify_fail", stage="chat_citation", reasons=check.reasons)

    payload["citations"] = kept
    answerable = bool(payload.get("answerable")) and bool(str(payload.get("answer", "")).strip())

    if answerable and not kept:
        trace("verify_fail", stage="chat", reason="no_valid_citation")
        payload = _refusal(
            "not_in_document",
            "Mình tìm được vài đoạn gần đúng nhưng không đoạn nào đủ để trả lời chắc chắn, "
            "nên không trả lời để tránh nói sai.",
            followup="Thử thu hẹp lại — ví dụ \"tóm tắt trang 12\" — tóm tắt một phạm vi "
                     "cho sẵn sẽ chính xác hơn.",
        )
        warnings.append("loại toàn bộ trích dẫn: câu trả lời không neo được vào tài liệu")
    elif not answerable:
        payload["citations"] = []

    payload["_meta"] = {
        "cached": False,
        "prompt_version": version,
        "model": settings().model_for("main"),
        "chunks": [
            {"page_no": r.chunk.page_no, "score": round(r.score, 3),
             "block_ids": r.chunk.block_ids}
            for r in results
        ],
        "pages": sorted({r.chunk.page_no for r in results}),
        "warnings": warnings,
    }
    return payload


def _refusal(reason: str, message: str, followup: str = "") -> dict:
    """Từ chối vẫn phải hữu ích: luôn kèm việc người dùng làm được tiếp theo."""
    return {
        "answerable": False,
        "answer": message,
        "citations": [],
        "refusal_reason": reason,
        "followup": followup or "Bạn có thể chọn một trang rồi tạo quiz để tự kiểm phần đó.",
        "confidence": "low",
        "_meta": {"cached": False, "chunks": [], "pages": [], "warnings": [], "no_call": True},
    }
