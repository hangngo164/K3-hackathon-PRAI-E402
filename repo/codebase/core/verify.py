from .models import Anchor


def verify_quote_in_text(quote: str, text: str) -> bool:
    normalized_quote = " ".join(quote.lower().split())
    normalized_text = " ".join(text.lower().split())
    return normalized_quote in normalized_text


def verify_anchor(anchor: Anchor, scope_ids: list[str]) -> bool:
    if f"p{anchor.page_no:02d}" not in scope_ids:
        return False
    return all(block_id in scope_ids for block_id in anchor.block_ids)
