"""Tìm đoạn liên quan trong tài liệu — chỉ phục vụ chat hỏi đáp.

Vì sao tồn tại: tóm tắt và quiz chạy trên phạm vi NGƯỜI DÙNG CHỌN, nên
`scope.py` biết trước được phép neo vào đâu. Chat thì câu hỏi gõ tự do, không
có phạm vi nào cho sẵn — phải tự tìm. Đây là chỗ duy nhất trong hệ thống mà
"phạm vi hợp lệ" là kết quả tìm kiếm chứ không phải cấu trúc tài liệu.

BM25 thuần Python, không embedding, không vector DB. Ba lý do:
  · thêm một dependency nặng cho một tính năng là cái giá không đáng
  · slide toàn thuật ngữ trùng khớp mặt chữ — khớp từ khoá đã bắt được phần lớn
  · chạy được offline, không tốn thêm một lời gọi API cho mỗi câu hỏi

Giới hạn phải nói thật khi demo: hỏi bằng từ đồng nghĩa mà slide không dùng thì
sẽ trượt. Bù lại, `tools/ask.py` cho model quyền trả `answerable=false` thay vì
đoán, nên trượt thì ra "không tìm thấy", không ra câu trả lời bịa.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from .models import Block, Document

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_BM25_K1 = 1.5
_BM25_B = 0.75
_MAX_CHUNK_CHARS = 700
_MIN_CHUNK_CHARS = 40
_TITLE_BOOST = 0.6  # khớp trọn câu hỏi vào tiêu đề slide => +60% điểm

# Từ xuất hiện ở mọi câu hỏi nên không mang thông tin để tìm. Cắt chúng đi để
# "Query/Key/Value là gì" không khớp với mọi trang có chữ "là".
# Viết có dấu cho người đọc; bản dùng để đối chiếu (`_STOPWORDS`) được bỏ dấu
# ngay sau khi `fold()` có mặt — `tokenize` bỏ dấu trước khi lọc, nên giữ bản có
# dấu ở đây thì không từ nối tiếng Việt nào bị chặn.
_STOPWORDS_RAW = {
    "là", "của", "và", "các", "có", "cho", "trong", "được", "một", "này", "đó",
    "khi", "thì", "với", "để", "ra", "vào", "về", "như", "không", "nào", "gì",
    "thế", "sao", "ạ", "nhé", "mình", "bạn", "tôi", "em", "anh", "chị", "ở",
    "hãy", "giúp", "hỏi", "nói", "biết", "hiểu", "nghĩa", "ý", "phần", "slide",
    "trang", "tài", "liệu", "the", "a", "an", "of", "is", "are", "what", "how",
    "why", "in", "on", "to", "and", "or", "for", "it", "this", "that",
}


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    page_no: int
    block_ids: list[str]
    text: str
    title: str = ""  # phần tiêu đề của slide, dùng để cộng điểm — xem _title_boost()


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float


def fold(text: str) -> str:
    """Bỏ dấu tiếng Việt: 'Hàm mất mát' -> 'ham mat mat'.

    Cần thiết vì rất nhiều người gõ câu hỏi KHÔNG DẤU, trong khi slide luôn có
    dấu — không bỏ dấu thì "ham mat mat" trượt sạch, hệ thống trả "không tìm
    thấy", và người dùng kết luận là công cụ không biết gì về tài liệu của họ.

    Đánh đổi đã cân nhắc: bỏ dấu làm 'má/mà/mã/mạ' chập thành một. Chấp nhận
    được, vì BM25 chấm trên nhiều từ khoá cùng lúc nên một từ chập không đủ kéo
    một đoạn không liên quan lên đầu, còn hỏng vì thiếu dấu thì hỏng hoàn toàn.
    """
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


_STOPWORDS = {fold(word) for word in _STOPWORDS_RAW}


def tokenize(text: str) -> list[str]:
    """Hạ chữ thường, BỎ DẤU, tách theo ký tự chữ-số Unicode, bỏ stopword.

    Cả hai phía (tài liệu và câu hỏi) đều đi qua đây nên luôn so khớp cùng một dạng.
    """
    return [
        token for token in (m.group(0) for m in _TOKEN_RE.finditer(fold(text)))
        if token not in _STOPWORDS and len(token) > 1
    ]


def build_chunks(doc: Document) -> list[Chunk]:
    """Gom khối liền nhau trong CÙNG một trang thành đoạn ~700 ký tự.

    Không cho một đoạn vắt qua hai trang: mọi đoạn phải neo được về đúng một
    `page_no`, nếu không thì trích dẫn `[trang N]` mất nghĩa và `verify.py`
    không kiểm được.
    """
    chunks: list[Chunk] = []
    for page in doc.pages:
        buffer: list[Block] = []
        size = 0
        for block in page.blocks:
            if buffer and size + len(block.text) > _MAX_CHUNK_CHARS:
                chunks.append(_make_chunk(page.page_no, buffer, len(chunks)))
                buffer, size = [], 0
            buffer.append(block)
            size += len(block.text) + 1
        if buffer:
            chunks.append(_make_chunk(page.page_no, buffer, len(chunks)))
    return [c for c in chunks if len(c.text.strip()) >= _MIN_CHUNK_CHARS]


def _make_chunk(page_no: int, blocks: list[Block], index: int) -> Chunk:
    return Chunk(
        chunk_id=f"c{index + 1:03d}",
        page_no=page_no,
        block_ids=[b.block_id for b in blocks],
        text="\n".join(b.text for b in blocks),
        title=" ".join(b.text for b in blocks if b.is_title_like),
    )


def _title_boost(query_terms: set[str], title: str) -> float:
    """Cộng điểm khi câu hỏi khớp vào TIÊU ĐỀ slide.

    Cần vì BM25 thuần xử slide rất tệ ở một trường hợp cụ thể và hay gặp: trang
    agenda liệt kê mọi chủ đề của buổi học. Nó ngắn, chứa đúng từ khoá, nên
    chuẩn hoá độ dài đẩy nó lên trên cả trang thật sự dạy chủ đề đó — và người
    hỏi nhận về đúng một dòng mục lục.

    Tiêu đề slide là tuyên bố "trang này nói về X", mạnh hơn nhiều so với một
    lần nhắc tên X trong danh sách. Đó là căn cứ của hệ số này.
    """
    if not title or not query_terms:
        return 1.0
    matched = query_terms & set(tokenize(title))
    return 1.0 + _TITLE_BOOST * (len(matched) / len(query_terms))


def search(chunks: list[Chunk], query: str, top_k: int = 6,
           min_score: float = 0.08) -> list[ScoredChunk]:
    """BM25, điểm đã chuẩn hoá về [0, 1] theo đoạn tốt nhất.

    Chuẩn hoá vì điểm BM25 thô không so sánh được giữa hai tài liệu khác nhau,
    mà `min_score` lại cần là một ngưỡng ổn định trong `.env`. Sau chuẩn hoá,
    ngưỡng đọc được là "đoạn này yếu hơn đoạn tốt nhất bao nhiêu".
    """
    query_tokens = tokenize(query)
    if not chunks or not query_tokens:
        return []

    docs = [tokenize(c.text) for c in chunks]
    lengths = [len(d) for d in docs]
    avg_length = sum(lengths) / len(lengths) if lengths else 1.0
    total = len(docs)

    frequency = Counter()
    for tokens in docs:
        frequency.update(set(tokens))

    idf = {
        term: math.log(1 + (total - frequency[term] + 0.5) / (frequency[term] + 0.5))
        for term in set(query_tokens) if frequency.get(term)
    }
    if not idf:
        return []  # không từ khoá nào của câu hỏi có mặt trong tài liệu

    matchable = set(idf)
    scored: list[ScoredChunk] = []
    for chunk, tokens, length in zip(chunks, docs, lengths):
        counts = Counter(tokens)
        score = sum(
            weight * counts[term] * (_BM25_K1 + 1)
            / (counts[term] + _BM25_K1 * (1 - _BM25_B + _BM25_B * length / avg_length))
            for term, weight in idf.items() if counts[term]
        )
        score *= _title_boost(matchable, chunk.title)
        if score > 0:
            scored.append(ScoredChunk(chunk=chunk, score=score))

    if not scored:
        return []
    best = max(s.score for s in scored)
    normalized = [ScoredChunk(chunk=s.chunk, score=s.score / best) for s in scored]
    normalized.sort(key=lambda s: (-s.score, s.chunk.page_no))
    return [s for s in normalized[:top_k] if s.score >= min_score]


def as_prompt_text(results: list[ScoredChunk]) -> str:
    """Bản GỬI CHO MODEL: có nhãn trang + id khối để đặt anchor đúng."""
    return "\n\n".join(
        f"[trang {r.chunk.page_no} · khối {', '.join(r.chunk.block_ids)}]\n{r.chunk.text}"
        for r in results
    )


def as_source_text(results: list[ScoredChunk]) -> str:
    """Bản ĐỂ VERIFY: chỉ nội dung, không nhãn.

    Tách khỏi `as_prompt_text` vì `verify.check_citation` so quote vào chuỗi
    này: nếu nhãn nằm trong đó thì một trích dẫn vắt qua ranh giới hai đoạn sẽ
    có "[trang 7 · khối ...]" chen giữa và bị loại oan.
    """
    return "\n\n".join(r.chunk.text for r in results)


def allowed_unit_ids(results: list[ScoredChunk]) -> list[str]:
    """Phạm vi hợp lệ cho trích dẫn của câu trả lời — `verify.check_citation` dùng."""
    ids: list[str] = []
    for result in results:
        ids.append(f"p{result.chunk.page_no:02d}")
        ids.extend(result.chunk.block_ids)
    return sorted(set(ids))
