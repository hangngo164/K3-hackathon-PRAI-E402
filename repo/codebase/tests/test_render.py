from core.render import pdf_to_px


def test_pdf_to_px_scales_pdf_points_at_110_dpi() -> None:
    assert pdf_to_px((72.0, 36.0, 144.0, 108.0), 110) == (110, 55, 220, 165)
