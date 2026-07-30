from typing import List

from .models import Chapter, Page, Section


def build_outline(pages: List[Page]) -> tuple[list[Chapter], str]:
    if not pages:
        return [], "flat"
    chapters = [Chapter(unit_id="ch01", title="Document", page_range=(1, len(pages)), sections=[])]
    return chapters, "flat"
