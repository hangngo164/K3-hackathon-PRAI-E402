from core.verify import verify_quote_in_text


def test_verify_quote_in_text_matches():
    text = "This is a sample slide text with some content."
    assert verify_quote_in_text("sample slide text", text)


def test_verify_quote_in_text_normalizes_whitespace():
    text = "This  is a sample slide text."
    assert verify_quote_in_text("sample    slide text", text)
