from pathlib import Path
from PIL import Image, ImageDraw


def pdf_to_px(bbox: tuple[float, float, float, float], dpi: int = 110) -> tuple[int, int, int, int]:
    scale = dpi / 72.0
    return tuple(int(coord * scale) for coord in bbox)


def draw_highlight(image_path: Path, boxes: list[tuple[int, int, int, int]], output_path: Path) -> Path:
    image = Image.open(image_path).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    for box in boxes:
        draw.rectangle(box, fill=(255, 255, 0, 96))
    result = Image.alpha_composite(image, overlay)
    result.convert("RGB").save(output_path)
    return output_path
