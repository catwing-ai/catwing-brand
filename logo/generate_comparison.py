"""
Generate a side-by-side comparison of top 4 font choices as composed logos.

Each font gets: vertical light, vertical dark, horizontal light, horizontal dark.
All on one sheet for easy comparison.

Usage:
    cd D:/_projects/__CAT_WING/logo
    python generate_comparison.py
"""

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
FONTS_DIR = SCRIPT_DIR / "fonts"
SOURCE_IMG = SCRIPT_DIR / "catwing_logo_1200x1200.png"
OUTPUT_FILE = SCRIPT_DIR / "comparison.png"
WIN_FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

TEXT = "CatWing"
TEXT_COLOR = "#1a1a2e"
TEXT_COLOR_RGBA = (26, 26, 46, 255)
DARK_BG = "#0f1923"
DARK_BG_RGBA = (15, 25, 35, 255)
DARK_TEXT_RGBA = (255, 255, 255, 255)
LETTER_SPACING_REF = 4

FONTS = [
    ("Sora SemiBold", "Sora-Variable.ttf", 600, "Japanese-inspired geometric"),
    ("Outfit Bold", "Outfit-Variable.ttf", 700, "Geometric, modern tech — bold"),
]


def load_font(file: str, size: int, variation: int | None) -> ImageFont.FreeTypeFont:
    path = FONTS_DIR / file
    font = ImageFont.truetype(str(path), size)
    if variation and hasattr(font, "set_variation_by_axes"):
        axes = font.get_variation_axes()
        axis_values = [
            variation if ax["name"] == b"wght" else ax.get("default", ax["minimum"])
            for ax in axes
        ]
        font.set_variation_by_axes(axis_values)
    return font


def scaled_spacing(font_size: int) -> int:
    return max(1, round(LETTER_SPACING_REF * font_size / 100))


def measure_text_spaced(font, text, spacing):
    if not text:
        return (0, 0)
    total_w = 0
    for i, ch in enumerate(text):
        bbox = font.getbbox(ch)
        total_w += bbox[2] - bbox[0]
        if i < len(text) - 1:
            total_w += spacing
    bbox_full = font.getbbox(text)
    return (total_w, bbox_full[3] - bbox_full[1])


def draw_text_spaced(draw, pos, text, font, fill, spacing):
    x, y = pos
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bbox = font.getbbox(ch)
        x += (bbox[2] - bbox[0]) + spacing


def auto_crop_alpha(img):
    img = img.convert("RGBA")
    a = np.array(img)
    alpha = a[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return img.crop((cmin, rmin, cmax + 1, rmax + 1))


def compose_vertical(cat, text, font_file, variation, text_color, bg_color, target_h):
    cat_h = int(target_h * 0.70)
    cat_w = int(cat.width * cat_h / cat.height)
    cat_resized = cat.resize((cat_w, cat_h), Image.LANCZOS)

    target_text_w = int(cat_w * 0.85)
    font_size = 10
    while font_size < 500:
        f = load_font(font_file, font_size, variation)
        sp = scaled_spacing(font_size)
        tw, _ = measure_text_spaced(f, text, sp)
        if tw >= target_text_w:
            break
        font_size += 1

    font = load_font(font_file, font_size, variation)
    sp = scaled_spacing(font_size)
    tw, th = measure_text_spaced(font, text, sp)

    gap = int(target_h * 0.04)
    pad_top = int(target_h * 0.03)
    pad_bottom = int(target_h * 0.06)
    total_h = pad_top + cat_h + gap + th + pad_bottom
    canvas_w = max(cat_w, tw) + int(target_h * 0.06)

    if bg_color:
        canvas = Image.new("RGBA", (canvas_w, total_h), bg_color)
    else:
        canvas = Image.new("RGBA", (canvas_w, total_h), (0, 0, 0, 0))

    cx = (canvas_w - cat_w) // 2
    canvas.paste(cat_resized, (cx, pad_top), cat_resized)

    draw = ImageDraw.Draw(canvas)
    tx = (canvas_w - tw) // 2
    ty = pad_top + cat_h + gap
    bbox_ref = font.getbbox(text)
    ty -= bbox_ref[1]
    draw_text_spaced(draw, (tx, ty), text, font, text_color, sp)
    return canvas


def compose_horizontal(cat, text, font_file, variation, text_color, bg_color, target_w, target_h):
    cat_h = int(target_h * 0.75)
    cat_w = int(cat.width * cat_h / cat.height)
    cat_resized = cat.resize((cat_w, cat_h), Image.LANCZOS)

    target_text_h = int(target_h * 0.18)
    font_size = 10
    while font_size < 300:
        f = load_font(font_file, font_size, variation)
        _, th = measure_text_spaced(f, text, scaled_spacing(font_size))
        if th >= target_text_h:
            break
        font_size += 1

    font = load_font(font_file, font_size, variation)
    sp = scaled_spacing(font_size)
    tw, th = measure_text_spaced(font, text, sp)

    gap = int(target_h * 0.08)
    pad_x = int(target_h * 0.06)
    needed_w = pad_x + cat_w + gap + tw + pad_x
    canvas_w = max(target_w, needed_w)

    if bg_color:
        canvas = Image.new("RGBA", (canvas_w, target_h), bg_color)
    else:
        canvas = Image.new("RGBA", (canvas_w, target_h), (0, 0, 0, 0))

    cy = (target_h - cat_h) // 2
    canvas.paste(cat_resized, (pad_x, cy), cat_resized)

    draw = ImageDraw.Draw(canvas)
    tx = pad_x + cat_w + gap
    bbox_ref = font.getbbox(text)
    ty = (target_h - th) // 2 - bbox_ref[1]
    draw_text_spaced(draw, (tx, ty), text, font, text_color, sp)
    return canvas


def paste_on_bg(img, bg_color, size):
    """Paste RGBA image onto a solid background, centered."""
    bg = Image.new("RGB", size, bg_color)
    # Center the image
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    bg.paste(img, (x, y), img)
    return bg


def main():
    cat = auto_crop_alpha(Image.open(SOURCE_IMG))
    print(f"Cat cropped: {cat.size}")

    # Layout: 4 fonts x 4 variants (vert-light, vert-dark, horiz-light, horiz-dark)
    # Each row = 1 font, columns = variants
    vert_target_h = 500
    horiz_target_w = 600
    horiz_target_h = 280

    # Generate all variants first to get actual sizes
    results = []
    for font_name, font_file, variation, desc in FONTS:
        print(f"Generating: {font_name}...")
        vl = compose_vertical(cat, TEXT, font_file, variation, TEXT_COLOR_RGBA, None, vert_target_h)
        vd = compose_vertical(cat, TEXT, font_file, variation, DARK_TEXT_RGBA, DARK_BG_RGBA, vert_target_h)
        hl = compose_horizontal(cat, TEXT, font_file, variation, TEXT_COLOR_RGBA, None, horiz_target_w, horiz_target_h)
        hd = compose_horizontal(cat, TEXT, font_file, variation, DARK_TEXT_RGBA, DARK_BG_RGBA, horiz_target_w, horiz_target_h)
        results.append((font_name, desc, vl, vd, hl, hd))

    # Determine cell sizes (use max dimensions)
    vert_cell_w = max(r[2].width for r in results) + 40
    vert_cell_h = max(r[2].height for r in results) + 20
    horiz_cell_w = max(r[4].width for r in results) + 40
    horiz_cell_h = max(r[4].height for r in results) + 20

    # Canvas layout
    label_w = 280
    gap = 16
    header_h = 100
    row_h = max(vert_cell_h, horiz_cell_h * 2 + gap) + 60  # extra for font label

    n_cols = 4  # vert-light, vert-dark, horiz-light, horiz-dark
    col_widths = [vert_cell_w, vert_cell_w, horiz_cell_w, horiz_cell_w]
    total_cols_w = sum(col_widths) + gap * (n_cols - 1)

    canvas_w = label_w + total_cols_w + gap * 2
    canvas_h = header_h + len(FONTS) * (row_h + gap) + gap
    canvas = Image.new("RGB", (canvas_w, canvas_h), "#e8e8e8")
    draw = ImageDraw.Draw(canvas)

    # Header
    try:
        title_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 30)
        col_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 18)
        label_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 22)
        desc_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeui.ttf"), 16)
    except Exception:
        title_font = col_font = label_font = desc_font = ImageFont.load_default()

    draw.text((20, 20), "CatWing Logo — Font Comparison (composed)", font=title_font, fill="#1a1a2e")
    draw.text((20, 58), "Top 4 fonts | charcoal text | light + dark backgrounds", font=desc_font, fill="#666666")

    # Column headers
    col_labels = ["Vertical / Light", "Vertical / Dark", "Horizontal / Light", "Horizontal / Dark"]
    col_x = label_w + gap
    for ci, (label, cw) in enumerate(zip(col_labels, col_widths)):
        cx = col_x + cw // 2
        bbox = col_font.getbbox(label)
        lw = bbox[2] - bbox[0]
        draw.text((cx - lw // 2, header_h - 30), label, font=col_font, fill="#444444")
        col_x += cw + gap

    # Render rows
    for ri, (font_name, desc, vl, vd, hl, hd) in enumerate(results):
        row_y = header_h + ri * (row_h + gap) + gap

        # Font label
        draw.text((16, row_y + 10), font_name, font=label_font, fill="#1a1a2e")
        draw.text((16, row_y + 38), desc, font=desc_font, fill="#777777")

        # Row number
        num_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 36)
        draw.text((label_w - 50, row_y + row_h // 2 - 20), str(ri + 1), font=num_font, fill="#cccccc")

        col_x = label_w + gap
        imgs = [vl, vd, hl, hd]
        bgs = ["#ffffff", DARK_BG, "#ffffff", DARK_BG]

        for ci, (img, bg, cw) in enumerate(zip(imgs, bgs, col_widths)):
            cell_h_actual = vert_cell_h if ci < 2 else horiz_cell_h
            # Create cell with background
            cell = paste_on_bg(img, bg, (cw, cell_h_actual))

            # Draw subtle border
            cell_draw = ImageDraw.Draw(cell)
            cell_draw.rectangle([0, 0, cw - 1, cell_h_actual - 1], outline="#bbbbbb", width=1)

            # Vertically center cell in row
            cy = row_y + (row_h - cell_h_actual) // 2
            canvas.paste(cell, (col_x, cy))
            col_x += cw + gap

    canvas.save(OUTPUT_FILE, "PNG")
    print(f"\nSaved: {OUTPUT_FILE} ({canvas_w}x{canvas_h})")
    os.startfile(str(OUTPUT_FILE))


if __name__ == "__main__":
    main()
