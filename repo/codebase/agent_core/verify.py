"""Lớp canh nguồn sự thật — kiểm bằng CODE, không bằng model.

Không gọi AI, không sửa nội dung: chỉ trả phán quyết + lý do. Việc loại bỏ hay
sửa là của `tools/`.

Chạy cho MỌI output trước khi tới UI. Fail thì loại và NÓI THẬT số lượng thực
tế ("chỉ tạo được 4/5 câu có căn cứ"), không im lặng hiển thị ít hơn.

Vì sao không nhờ model tự kiểm: model chấm chính nó thì sai cùng chiều với lúc
nó sinh. Mọi luật dưới đây đều là thứ so khớp được bằng chuỗi và số đếm.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

from .models import Anchor, ScopeContext

# Câu hỏi về HÌNH THỨC tài liệu thay vì nội dung — vô dụng cho việc ôn tập,
# và là dấu hiệu model đã cạn căn cứ nên bắt đầu mô tả trang giấy.
_FORM_QUESTION_PATTERNS = [
    r"bao nhiêu\s+(bullet|gạch đầu dòng|mục|dòng|ý|hình|ảnh|biểu đồ)",
    r"có mấy\s+(bullet|gạch đầu dòng|mục|dòng|ý|hình|ảnh)",
    r"tiêu đề của (slide|trang)",
    r"(slide|trang) (này |)(có |)tên (là |)gì",
    r"nằm ở (slide|trang) (số |)mấy",
    r"how many (bullets|points|items|slides)",
    r"what is the (slide|page) title",
]

_BANNED_OPTIONS = [
    "tất cả các đáp án trên", "tất cả đều đúng", "tất cả các phương án trên",
    "không đáp án nào", "không phương án nào", "không có đáp án nào đúng",
    "all of the above", "none of the above", "both a and b",
]

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
_MAX_OPTION_LENGTH_RATIO = 2.5
_MIN_ANSWER_LEAK_CHARS = 8


@dataclass(frozen=True)
class CheckResult:
    passed: bool
    reasons: list[str]
    warnings: list[str] = field(default_factory=list)

    def merged(self, other: "CheckResult") -> "CheckResult":
        return CheckResult(
            passed=self.passed and other.passed,
            reasons=self.reasons + other.reasons,
            warnings=self.warnings + other.warnings,
        )


def normalize(text: str) -> str:
    """Gộp whitespace + lower — dùng cho CẢ HAI phía khi so khớp."""
    return " ".join(text.lower().split())


def verify_quote_in_text(quote: str, text: str) -> bool:
    """Khớp tuyệt đối sau normalize."""
    return normalize(quote) in normalize(text)


def quote_matches(quote: str, source: str, threshold: float = 0.92) -> bool:
    """Khớp tuyệt đối; không được thì fuzzy >= threshold.

    Cần fuzzy vì model rất hay "sửa hộ" dấu câu, gạch nối, khoảng trắng trong
    trích dẫn. Ngưỡng 0.92 đủ chặt để một câu bịa không lọt, đủ lỏng để một
    trích dẫn thật bị đổi dấu phẩy không bị loại oan.
    """
    if verify_quote_in_text(quote, source):
        return True
    nq, ns = normalize(quote), normalize(source)
    if not nq or len(nq) > len(ns):
        return False
    window = len(nq)
    for start in range(0, len(ns) - window + 1, max(1, window // 4)):
        if difflib.SequenceMatcher(None, nq, ns[start:start + window]).ratio() >= threshold:
            return True
    return False


def anchor_from_dict(raw: dict) -> Anchor:
    """dict của model -> Anchor. Field thiếu/sai kiểu => giá trị an toàn, để check bắt sau."""
    try:
        page_no = int(raw.get("page_no", 0) or 0)
    except (TypeError, ValueError):
        page_no = 0
    block_ids = raw.get("block_ids") or []
    if not isinstance(block_ids, list):
        block_ids = []
    return Anchor(
        page_no=page_no,
        block_ids=[str(b) for b in block_ids],
        quote=str(raw.get("quote", "") or ""),
    )


def verify_anchor(anchor: Anchor, scope_ids: list[str]) -> bool:
    """page_no và mọi block_id phải nằm trong unit_ids của scope (không rò trang ngoài)."""
    if f"p{anchor.page_no:02d}" not in scope_ids:
        return False
    return all(block_id in scope_ids for block_id in anchor.block_ids)


def check_anchor(anchor: Anchor, ctx: ScopeContext) -> CheckResult:
    """Quote tồn tại · page_no hợp lệ · block_ids thuộc scope."""
    reasons: list[str] = []
    if not verify_anchor(anchor, ctx.unit_ids):
        reasons.append(f"anchor trỏ ra ngoài scope: trang {anchor.page_no}, khối {anchor.block_ids}")
    if not anchor.quote.strip():
        reasons.append("anchor thiếu quote")
    elif not quote_matches(anchor.quote, ctx.text):
        reasons.append(f"quote không có trong nguồn: {anchor.quote[:60]!r}")
    return CheckResult(passed=not reasons, reasons=reasons)


def check_numbers(text: str, source: str) -> CheckResult:
    """Mọi số trong output phải xuất hiện trong nguồn.

    Trả WARNING chứ không fail: số có thể là kết quả đếm hợp lệ ("3 bước") mà
    nguồn không viết ra thành chữ số. Loại thẳng thì mất câu đúng; cảnh báo thì
    người dùng biết chỗ cần liếc lại. Sai ở đây rẻ, nên không chặn.
    """
    in_source = {n.replace(",", "").replace(".", "") for n in _NUMBER_RE.findall(source)}
    missing = [
        n for n in _NUMBER_RE.findall(text)
        if n.replace(",", "").replace(".", "") not in in_source
    ]
    unique = sorted(set(missing))
    return CheckResult(
        passed=True,
        reasons=[],
        warnings=[f"số không thấy trong nguồn: {', '.join(unique)}"] if unique else [],
    )


def check_bullet(bullet: dict, ctx: ScopeContext) -> CheckResult:
    """Một bullet tóm tắt: phải có nội dung và một neo kiểm được."""
    text = str(bullet.get("text", "") or "").strip()
    if not text:
        return CheckResult(passed=False, reasons=["bullet rỗng"])
    result = check_anchor(anchor_from_dict(bullet.get("anchor") or {}), ctx)
    return result.merged(check_numbers(text, ctx.text))


def check_summary(payload: dict, ctx: ScopeContext, *, max_length_ratio: float = 0.6) -> CheckResult:
    """Luật ở mức cả bản tóm tắt, sau khi từng bullet đã được kiểm riêng.

    Ràng buộc độ dài chỉ áp cho scope hẹp nhất (một trang): tóm tắt dài hơn 60%
    bản gốc thì nó không còn là tóm tắt. Với chương/tài liệu thì vô nghĩa vì
    nguồn lớn hơn output hàng chục lần.
    """
    reasons: list[str] = []
    warnings: list[str] = []

    if not str(payload.get("tldr", "") or "").strip():
        reasons.append("thiếu tldr")

    bullets = payload.get("bullets") or []
    confidence = payload.get("confidence")
    if not bullets and confidence != "low":
        reasons.append("không có bullet nào nhưng confidence không phải 'low'")

    if ctx.scope == "page":
        produced = len(str(payload.get("tldr", ""))) + sum(
            len(str(b.get("text", ""))) for b in bullets
        )
        budget = len(ctx.text) * max_length_ratio
        if ctx.text and produced > budget:
            warnings.append(
                f"tóm tắt dài {produced} ký tự trên nguồn {len(ctx.text)} ký tự "
                f"(>{int(max_length_ratio * 100)}%)"
            )

    return CheckResult(passed=not reasons, reasons=reasons, warnings=warnings)


def check_quiz_item(item: dict, ctx: ScopeContext) -> CheckResult:
    """Luật chống câu hỏi rác.

    Thứ tự kiểm đi từ rẻ đến đắt và từ chắc chắn đến suy đoán; mọi luật ở đây
    đều là thứ một người soạn đề sẽ loại ngay khi nhìn thấy.
    """
    reasons: list[str] = []
    warnings: list[str] = []

    stem = str(item.get("stem", "") or "").strip()
    answer_text = str(item.get("answer_text", "") or "").strip()
    options = item.get("options") or []
    options = [str(o) for o in options] if isinstance(options, list) else []
    item_type = item.get("type")
    try:
        answer_index = int(item.get("answer_index", -1))
    except (TypeError, ValueError):
        answer_index = -1

    if not stem:
        reasons.append("thiếu stem")
    if not answer_text:
        reasons.append("thiếu answer_text")
    if not str(item.get("explanation", "") or "").strip():
        reasons.append("thiếu explanation")

    # 1. Neo nguồn — điều kiện để câu hỏi được phép hiển thị
    reasons += check_anchor(anchor_from_dict(item.get("anchor") or {}), ctx).reasons

    # 2. Hình dạng phương án theo từng loại câu
    if item_type == "short_answer":
        if options:
            reasons.append("short_answer không được có options")
        if answer_index != -1:
            reasons.append("short_answer phải có answer_index = -1")
    else:
        expected = 2 if item_type == "true_false" else 4
        if len(options) != expected:
            reasons.append(f"{item_type} cần đúng {expected} phương án, đang có {len(options)}")
        if not 0 <= answer_index < len(options):
            reasons.append(f"answer_index={answer_index} nằm ngoài danh sách phương án")
        if len({normalize(o) for o in options}) != len(options):
            reasons.append("có hai phương án trùng nhau")
        if any(any(bad in normalize(o) for bad in _BANNED_OPTIONS) for o in options):
            reasons.append("dùng phương án kiểu 'tất cả các đáp án trên'")

    # 3. Độ dài phương án: đáp án đúng dài gấp bội là mẹo đoán, không phải kiến thức
    if item_type == "mcq" and len(options) > 1:
        lengths = [len(o.strip()) for o in options if o.strip()]
        if lengths and min(lengths) > 0 and max(lengths) / min(lengths) > _MAX_OPTION_LENGTH_RATIO:
            reasons.append(
                f"độ dài phương án chênh {max(lengths) / min(lengths):.1f}x "
                f"(> {_MAX_OPTION_LENGTH_RATIO}x)"
            )

    # 4. Stem lộ đáp án
    if answer_text and len(answer_text) >= _MIN_ANSWER_LEAK_CHARS:
        if normalize(answer_text) in normalize(stem):
            reasons.append("stem chứa nguyên văn đáp án")

    # 5. Hỏi về hình thức tài liệu thay vì nội dung
    stem_norm = normalize(stem)
    if any(re.search(pattern, stem_norm) for pattern in _FORM_QUESTION_PATTERNS):
        reasons.append("câu hỏi về hình thức tài liệu, không phải nội dung")

    # 6. Giải thích của phương án nhiễu — thiếu thì cảnh báo, không loại câu
    if item_type == "mcq":
        rationale = item.get("distractor_rationale") or []
        if isinstance(rationale, list) and len(rationale) < max(0, len(options) - 1):
            warnings.append(
                f"chỉ giải thích {len(rationale)}/{max(0, len(options) - 1)} phương án nhiễu"
            )

    numbers = check_numbers(f"{stem} {answer_text} {item.get('explanation', '')}", ctx.text)
    warnings += numbers.warnings

    return CheckResult(passed=not reasons, reasons=reasons, warnings=warnings)


def check_citation(anchor: Anchor, allowed_unit_ids: list[str], source_text: str) -> CheckResult:
    """Neo của câu trả lời chat.

    Khác `check_anchor` ở chỗ phạm vi hợp lệ là CÁC ĐOẠN ĐÃ TÌM ĐƯỢC, không
    phải một scope người dùng chọn — nên nhận `allowed_unit_ids` rời thay vì
    một ScopeContext.
    """
    reasons: list[str] = []
    if f"p{anchor.page_no:02d}" not in allowed_unit_ids:
        reasons.append(f"trích dẫn trỏ tới trang {anchor.page_no} không nằm trong đoạn đã tìm")
    if not all(bid in allowed_unit_ids for bid in anchor.block_ids):
        reasons.append(f"trích dẫn trỏ tới khối ngoài đoạn đã tìm: {anchor.block_ids}")
    if not anchor.quote.strip():
        reasons.append("trích dẫn thiếu quote")
    elif not quote_matches(anchor.quote, source_text):
        reasons.append(f"quote không có trong đoạn đã tìm: {anchor.quote[:60]!r}")
    return CheckResult(passed=not reasons, reasons=reasons)
