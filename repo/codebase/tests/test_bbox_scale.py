from core.render import pdf_to_px


def test_pdf_to_px_scaling():
    bbox = (72.0, 72.0, 144.0, 144.0)
    result = pdf_to_px(bbox, dpi=110)
    assert result == (110, 110, 220, 220)
