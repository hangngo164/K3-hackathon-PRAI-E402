from typing import Literal

from .models import Anchor, Document, ScopeContext

Scope = Literal["document", "chapter", "section", "page", "selection"]


def resolve(doc: Document, scope: Scope, target_id: str | None,
            selection: Anchor | None) -> ScopeContext:
    if scope == "selection" and selection is not None:
        return ScopeContext(
            scope=scope,
            unit_ids=[f"p{selection.page_no:02d}"],
            text=selection.quote,
            est_tokens=max(1, len(selection.quote) // 4),
            strategy="direct",
            anchors_available=[selection],
        )
    page_no = int(target_id) if target_id is not None else 1
    page = next((p for p in doc.pages if p.page_no == page_no), None)
    if page is None:
        raise ValueError("Page not found")
    return ScopeContext(
        scope="page",
        unit_ids=[f"p{page.page_no:02d}"],
        text=page.text,
        est_tokens=max(1, len(page.text) // 4),
        strategy="direct",
        anchors_available=[Anchor(page_no=page.page_no, block_ids=[b.block_id for b in page.blocks], quote=page.text[:200])],
    )
