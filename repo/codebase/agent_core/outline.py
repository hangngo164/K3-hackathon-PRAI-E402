"""Dò chương/mục theo thang 4 bậc, dừng ở bậc ĐẦU TIÊN thành công.

    1. toc        bookmark có sẵn trong PDF — chắc nhất, miễn phí
    2. heuristic  slide phân cách + tiêu đề lặp — không tốn lời gọi nào
    3. llm        một lời gọi trên DANH SÁCH TIÊU ĐỀ TRANG (không phải toàn văn)
    4. flat       không tách được — chỉ còn document + page

Bậc 4 KHÔNG phải lỗi: UI nói rõ lý do và tắt tóm tắt/quiz theo chương kèm giải
thích, thay vì hiện nút bấm vào ra rác.

Module thuần logic nhóm: KHÔNG mở PDF (ingest truyền `toc` vào), KHÔNG gọi model
(caller truyền hàm `grouper` vào). Nhờ vậy test được bằng dữ liệu bịa, và luật
phụ thuộc `agent_core` không import `providers` vẫn giữ nguyên.
"""

from __future__ import annotations

from statistics import median
from typing import Callable, Iterable

from .models import Chapter, Page, Section

# Hàm bậc 3 do `tools/outline.py` cấp: danh sách "trang N: tiêu đề" -> chapters thô
Grouper = Callable[[list[str], int], list[dict] | None]

_TITLE_TOP_RATIO = 0.45   # tiêu đề nằm trong 45% trên của trang
_TITLE_FONT_RATIO = 1.15  # và to hơn cỡ chữ thân bài 15%
_DIVIDER_MAX_BLOCKS = 3   # slide phân cách chương: rất ít chữ, một dòng tiêu đề to
_MIN_CHAPTERS = 2         # dưới ngưỡng này thì "cấu trúc" không đáng gọi là cấu trúc


def build_outline(
    pages: list[Page],
    toc: list | None = None,
    grouper: Grouper | None = None,
) -> tuple[list[Chapter], str]:
    """Trả `(chapters, outline_source)`.

    Không bao giờ dựng một chương giả tên "Document": `outline_source='flat'` mà
    vẫn có chương là nói dối UI, và tóm tắt theo chương sẽ chạy trên một cấu
    trúc không có thật.
    """
    if not pages:
        return [], "flat"
    total = len(pages)

    chapters = from_toc(toc, total)
    if chapters:
        return chapters, "toc"

    chapters = from_heuristic(pages)
    if chapters:
        return chapters, "heuristic"

    if grouper is not None:
        chapters = from_llm(pages, grouper)
        if chapters:
            return chapters, "llm"

    return [], "flat"


# --- Bậc 1: mục lục có sẵn trong PDF ---

def from_toc(toc: list | None, total_pages: int) -> list[Chapter] | None:
    """`toc` là kết quả `fitz.Document.get_toc()`: [[level, title, page_1based], ...].

    Chỉ nhận level 1 làm chương và level 2 làm mục. Level sâu hơn bị gộp lên
    level 2: slide hiếm khi có cấu trúc quá hai tầng, và đào sâu hơn chỉ làm
    cây trên sidebar rối mà không giúp chọn phạm vi tốt hơn.
    """
    if not toc:
        return None

    entries = []
    for row in toc:
        try:
            level, title, page_no = int(row[0]), str(row[1]).strip(), int(row[2])
        except (TypeError, ValueError, IndexError):
            continue
        if title and 1 <= page_no <= total_pages:
            entries.append((min(level, 2), title, page_no))
    if not entries:
        return None

    entries.sort(key=lambda e: e[2])
    if not any(level == 1 for level, _, _ in entries):
        return None

    raw: list[dict] = []
    for level, title, page_no in entries:
        if level == 1 or not raw:
            raw.append({"title": title, "start_page": page_no, "sections": []})
        else:
            raw[-1]["sections"].append({"title": title, "start_page": page_no})

    chapters = _build_from_starts(raw, total_pages)
    return chapters if len(chapters) >= _MIN_CHAPTERS else None


# --- Bậc 2: suy từ hình thức trang ---

def page_title(page: Page, body_font: float) -> str | None:
    """Tiêu đề của một trang: khối chữ to nhất nằm ở nửa trên.

    Trả None khi trang không có khối nào nổi bật — trang nội dung thuần hoặc
    trang toàn hình.
    """
    if not page.blocks:
        return None
    page_bottom = max((b.bbox[3] for b in page.blocks), default=0.0)
    if page_bottom <= 0:
        return None

    candidates = [
        b for b in page.blocks
        if b.bbox[1] <= page_bottom * _TITLE_TOP_RATIO
        and b.font_size_max >= body_font * _TITLE_FONT_RATIO
        and b.text.strip()
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda b: (b.font_size_max, -b.bbox[1]))
    return " ".join(best.text.split())[:120]


def from_heuristic(pages: list[Page]) -> list[Chapter] | None:
    """Slide phân cách chương = trang rất ít khối + có tiêu đề to.

    Đây là quy ước gần như phổ quát của slide bài giảng: một trang chỉ ghi tên
    phần rồi sang nội dung. Nếu deck không theo quy ước đó, hàm này trả None và
    thang tụt xuống bậc LLM — đúng ý đồ, không cố đoán bừa.
    """
    body_font = _body_font_size(pages)
    titles = {p.page_no: page_title(p, body_font) for p in pages}

    dividers = [
        p.page_no for p in pages
        if titles.get(p.page_no) and len(p.blocks) <= _DIVIDER_MAX_BLOCKS
    ]
    # Trang bìa không phải phân cách chương; bỏ nếu nó là divider đầu tiên ở trang 1
    dividers = [n for n in dividers if n > 1] or dividers

    if len(dividers) < _MIN_CHAPTERS:
        return None

    raw = [{"title": titles[n] or f"Phần {i + 1}", "start_page": n, "sections": []}
           for i, n in enumerate(dividers)]
    if dividers[0] > 1:
        raw.insert(0, {"title": titles.get(1) or "Mở đầu", "start_page": 1, "sections": []})

    chapters = _build_from_starts(raw, len(pages))
    if len(chapters) < _MIN_CHAPTERS:
        return None
    return [_split_sections_by_title(ch, pages, titles) for ch in chapters]


def _body_font_size(pages: list[Page]) -> float:
    sizes = [b.font_size_max for p in pages for b in p.blocks if b.font_size_max > 0]
    return median(sizes) if sizes else 12.0


def _split_sections_by_title(chapter: Chapter, pages: list[Page],
                             titles: dict[int, str | None]) -> Chapter:
    """Trong một chương, các trang liên tiếp CÙNG tiêu đề là một mục.

    Slide hay tách một ý ra 2-3 trang mà giữ nguyên tiêu đề; gom lại đúng bằng
    cách đó thì phạm vi "mục" khớp với cách người dạy chia bài.
    """
    start, end = chapter.page_range
    runs: list[tuple[str, int, int]] = []
    for page_no in range(start, end + 1):
        title = titles.get(page_no)
        if title and runs and runs[-1][0] == title:
            runs[-1] = (title, runs[-1][1], page_no)
        elif title:
            runs.append((title, page_no, page_no))
        elif runs:
            runs[-1] = (runs[-1][0], runs[-1][1], page_no)

    if len(runs) < 2:
        return chapter  # một mục duy nhất thì không phải cấu trúc, để trống

    sections = [
        Section(
            unit_id=f"{chapter.unit_id}-s{index:02d}",
            title=title,
            page_range=(first, last),
            chapter_id=chapter.unit_id,
        )
        for index, (title, first, last) in enumerate(runs, start=1)
    ]
    return Chapter(
        unit_id=chapter.unit_id,
        title=chapter.title,
        page_range=chapter.page_range,
        sections=sections,
    )


# --- Bậc 3: nhờ model gom, nhưng chỉ trên tiêu đề trang ---

def page_title_lines(pages: list[Page]) -> list[str]:
    """Đầu vào cho bậc 3. CHỈ tiêu đề — không đưa toàn văn tài liệu vào prompt."""
    body_font = _body_font_size(pages)
    lines = []
    for page in pages:
        title = page_title(page, body_font) or (page.text.strip().split("\n") or [""])[0][:120]
        lines.append(f"trang {page.page_no}: {title.strip() or '(trang không có chữ)'}")
    return lines


def from_llm(pages: list[Page], grouper: Grouper) -> list[Chapter] | None:
    """Gọi hàm gom nhóm do tầng trên cấp, rồi KIỂM LẠI bằng code.

    Model có thể trả khoảng trang chồng lấn, thủng lỗ, hoặc vượt số trang thật.
    `_build_from_starts` chỉ tin `start_page` và tự tính lại `end_page`, nên
    mọi khoảng luôn liền nhau và phủ đúng tài liệu — kể cả khi model trả bậy.
    """
    try:
        raw = grouper(page_title_lines(pages), len(pages))
    except Exception:
        return None  # bậc 3 hỏng thì tụt xuống 'flat', không làm chết việc nạp file
    if not raw:
        return None

    cleaned: list[dict] = []
    for chapter in raw:
        try:
            start = int(chapter.get("start_page", 0))
        except (TypeError, ValueError):
            continue
        title = str(chapter.get("title", "") or "").strip()
        if title and 1 <= start <= len(pages):
            cleaned.append({
                "title": title,
                "start_page": start,
                "sections": [
                    {"title": str(s.get("title", "") or "").strip(),
                     "start_page": int(s.get("start_page", 0) or 0)}
                    for s in (chapter.get("sections") or [])
                    if str(s.get("title", "") or "").strip()
                ],
            })

    chapters = _build_from_starts(cleaned, len(pages))
    return chapters if len(chapters) >= _MIN_CHAPTERS else None


# --- Dựng khoảng trang: nguồn sự thật duy nhất cho cả ba bậc trên ---

def _build_from_starts(raw: list[dict], total_pages: int) -> list[Chapter]:
    """Chỉ tin `start_page`; `end_page` luôn TỰ TÍNH.

    Ba bậc trên đều có thể cho khoảng trang chồng lấn hoặc thủng lỗ. Tự tính
    end_page = (start của mục kế) - 1 làm cho tính chất "liền nhau, không chồng
    lấn, phủ hết tài liệu" thành đúng theo cấu tạo, không phải thứ phải đi kiểm.
    """
    entries = _dedupe_by_start(raw)
    if not entries:
        return []
    if entries[0]["start_page"] > 1:
        entries[0] = {**entries[0], "start_page": 1}

    chapters: list[Chapter] = []
    for index, entry in enumerate(entries):
        start = entry["start_page"]
        end = entries[index + 1]["start_page"] - 1 if index + 1 < len(entries) else total_pages
        if end < start:
            continue
        unit_id = f"ch{index + 1:02d}"
        chapters.append(Chapter(
            unit_id=unit_id,
            title=entry["title"],
            page_range=(start, end),
            sections=_build_sections(entry.get("sections") or [], unit_id, start, end),
        ))
    return chapters


def _build_sections(raw: list[dict], chapter_id: str, start: int, end: int) -> list[Section]:
    entries = [s for s in _dedupe_by_start(raw) if start <= s["start_page"] <= end]
    if len(entries) < 2:
        return []
    if entries[0]["start_page"] > start:
        entries[0] = {**entries[0], "start_page": start}

    sections: list[Section] = []
    for index, entry in enumerate(entries):
        first = entry["start_page"]
        last = entries[index + 1]["start_page"] - 1 if index + 1 < len(entries) else end
        if last < first:
            continue
        sections.append(Section(
            unit_id=f"{chapter_id}-s{index + 1:02d}",
            title=entry["title"],
            page_range=(first, last),
            chapter_id=chapter_id,
        ))
    return sections


def _dedupe_by_start(raw: Iterable[dict]) -> list[dict]:
    """Sắp theo start_page, mỗi trang chỉ được mở đúng một mục."""
    seen: dict[int, dict] = {}
    for entry in raw:
        start = entry.get("start_page")
        if isinstance(start, int) and start >= 1 and start not in seen:
            seen[start] = entry
    return [seen[key] for key in sorted(seen)]


# --- Tra cứu dùng chung cho scope.py và UI ---

def find_chapter(chapters: list[Chapter], unit_id: str) -> Chapter | None:
    return next((c for c in chapters if c.unit_id == unit_id), None)


def find_section(chapters: list[Chapter], unit_id: str) -> Section | None:
    for chapter in chapters:
        for section in chapter.sections:
            if section.unit_id == unit_id:
                return section
    return None


def outline_digest(chapters: list[Chapter]) -> str:
    """Cây chương/mục dạng text cho prompt điều phối — CÓ `unit_id`.

    Cùng lý lẽ với `page_title_lines()`: đưa cấu trúc vào prompt, không đưa nội
    dung. Có `unit_id` trong đó thì model trả về được đúng id có thật thay vì tự
    đặt tên phần, và `agent_core/intent.py` khỏi phải đoán ý nó.

    Không có chương nào ⇒ trả "" để caller nói thẳng tài liệu này chỉ chọn được
    theo trang, thay vì gửi một cây rỗng rồi để model tưởng có cấu trúc.
    """
    lines: list[str] = []
    for chapter in chapters:
        first, last = chapter.page_range
        lines.append(f"- {chapter.unit_id} · {chapter.title} (trang {first}-{last})")
        for section in chapter.sections:
            s_first, s_last = section.page_range
            lines.append(f"    - {section.unit_id} · {section.title} (trang {s_first}-{s_last})")
    return "\n".join(lines)


def unit_label(chapters: list[Chapter], unit_id: str) -> str:
    """Nhãn người đọc được: 'Chương 2 › Mục 3 (trang 12-18)'."""
    chapter = find_chapter(chapters, unit_id)
    if chapter:
        return f"{chapter.title} (trang {chapter.page_range[0]}-{chapter.page_range[1]})"
    section = find_section(chapters, unit_id)
    if section:
        parent = find_chapter(chapters, section.chapter_id)
        prefix = f"{parent.title} › " if parent else ""
        return f"{prefix}{section.title} (trang {section.page_range[0]}-{section.page_range[1]})"
    return unit_id
