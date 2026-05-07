"""
Phase 1: Generate a visual sample sheet for CatWing logo wordmark.

Shows 12 distinctive Google Fonts, each in 3 light-bg colors + 1 dark-bg = 4 columns.
Casing fixed to "CatWing" (PascalCase).

Usage:
    cd D:/_projects/__CAT_WING/logo
    python generate_samples.py
"""

import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
FONTS_DIR = SCRIPT_DIR / "fonts"
SOURCE_IMG = SCRIPT_DIR / "catwing_logo_1200x1200.png"
OUTPUT_FILE = SCRIPT_DIR / "samples.png"

TEXT = "CatWing"

BG_LIGHT = "#ffffff"
BG_DARK = "#0f1923"
LIGHT_COLORS = [
    ("#1a1a2e", "charcoal"),
    ("#3064b6", "blue"),
    ("#20b0a5", "teal"),
]
TEXT_COLOR_DARK = "#ffffff"

# Cell dimensions
CELL_W = 480
CELL_H = 140
FONT_SIZE = 72
LETTER_SPACING = 3

# Grid layout
LABEL_W = 340
GAP = 10
HEADER_H = 320

# ---------------------------------------------------------------------------
# Google Fonts — 12 distinctive, non-commodity fonts
# ---------------------------------------------------------------------------
GOOGLE_FONTS = {
    # Geometric / tech-forward
    "Outfit SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/outfit/Outfit%5Bwght%5D.ttf",
        "file": "Outfit-Variable.ttf",
        "variation": 600,
        "desc": "Geometric, modern tech",
    },
    "Sora SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/sora/Sora%5Bwght%5D.ttf",
        "file": "Sora-Variable.ttf",
        "variation": 600,
        "desc": "Japanese-inspired geometric",
    },
    "Urbanist SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/urbanist/Urbanist%5Bwght%5D.ttf",
        "file": "Urbanist-Variable.ttf",
        "variation": 600,
        "desc": "Ultra-clean geometric",
    },
    "Albert Sans SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/albertsans/AlbertSans%5Bwght%5D.ttf",
        "file": "AlbertSans-Variable.ttf",
        "variation": 600,
        "desc": "Geometric grotesk",
    },
    # Humanist / warm professional
    "Plus Jakarta Sans SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf",
        "file": "PlusJakartaSans-Variable.ttf",
        "variation": 600,
        "desc": "Warm professional, Stripe-like",
    },
    "Manrope SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf",
        "file": "Manrope-Variable.ttf",
        "variation": 600,
        "desc": "Modern humanist sans",
    },
    "Figtree SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/figtree/Figtree%5Bwght%5D.ttf",
        "file": "Figtree-Variable.ttf",
        "variation": 600,
        "desc": "Friendly geometric",
    },
    # Display / distinctive
    "Red Hat Display SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/redhatdisplay/RedHatDisplay%5Bwght%5D.ttf",
        "file": "RedHatDisplay-Variable.ttf",
        "variation": 600,
        "desc": "Pentagram-designed display",
    },
    "Bricolage Grotesque SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf",
        "file": "BricolageGrotesque-Variable.ttf",
        "variation": 600,
        "desc": "Expressive grotesque",
    },
    "Epilogue SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/epilogue/Epilogue%5Bwght%5D.ttf",
        "file": "Epilogue-Variable.ttf",
        "variation": 600,
        "desc": "Post-grotesk display",
    },
    "Onest SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/onest/Onest%5Bwght%5D.ttf",
        "file": "Onest-Variable.ttf",
        "variation": 600,
        "desc": "Rounded geometric, friendly",
    },
    # Readability / unique
    "Lexend SemiBold": {
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/lexend/Lexend%5Bwght%5D.ttf",
        "file": "Lexend-Variable.ttf",
        "variation": 600,
        "desc": "Optimized for readability",
    },
}

WIN_FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"


def download_fonts():
    """Download Google Fonts if not already cached."""
    FONTS_DIR.mkdir(exist_ok=True)
    for name, info in GOOGLE_FONTS.items():
        dest = FONTS_DIR / info["file"]
        if dest.exists():
            continue
        print(f"Downloading {name}...")
        try:
            urllib.request.urlretrieve(info["url"], dest)
            print(f"  -> {dest.name}")
        except Exception as e:
            print(f"  FAILED: {e}")


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont | None:
    """Load a font by name. Returns None if unavailable."""
    if name not in GOOGLE_FONTS:
        return None
    info = GOOGLE_FONTS[name]
    path = FONTS_DIR / info["file"]
    if not path.exists():
        return None
    font = ImageFont.truetype(str(path), size)
    if info.get("variation") and hasattr(font, "set_variation_by_axes"):
        try:
            axes = font.get_variation_axes()
            axis_values = [
                info["variation"] if ax["name"] == b"wght"
                else ax.get("default", ax["minimum"])
                for ax in axes
            ]
            font.set_variation_by_axes(axis_values)
        except Exception as e:
            print(f"  Warning: variation failed for {name}: {e}")
    return font


def measure_text_spaced(font: ImageFont.FreeTypeFont, text: str, spacing: int) -> int:
    """Measure text width with letter-spacing using getbbox()."""
    if not text:
        return 0
    total = 0
    for i, ch in enumerate(text):
        bbox = font.getbbox(ch)
        total += bbox[2] - bbox[0]
        if i < len(text) - 1:
            total += spacing
    return total


def draw_text_spaced(draw, pos, text, font, fill, spacing):
    """Draw text character-by-character with letter-spacing."""
    x, y = pos
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bbox = font.getbbox(ch)
        x += (bbox[2] - bbox[0]) + spacing


def auto_crop_alpha(img: Image.Image) -> Image.Image:
    """Crop to content bounds based on alpha channel."""
    img = img.convert("RGBA")
    a = np.array(img)
    alpha = a[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return img.crop((cmin, rmin, cmax + 1, rmax + 1))


def render_cell(text, font, bg_color, text_color):
    """Render a single sample cell."""
    cell = Image.new("RGB", (CELL_W, CELL_H), bg_color)
    draw = ImageDraw.Draw(cell)

    tw = measure_text_spaced(font, text, LETTER_SPACING)
    bbox = font.getbbox(text)
    th = bbox[3] - bbox[1]
    x = (CELL_W - tw) // 2
    y = (CELL_H - th) // 2 - bbox[1]

    draw_text_spaced(draw, (x, y), text, font, text_color, LETTER_SPACING)

    # Subtle border
    draw.rectangle([0, 0, CELL_W - 1, CELL_H - 1], outline="#d0d0d0", width=1)
    return cell


def main():
    download_fonts()

    # Load all fonts
    fonts = {}
    for name in GOOGLE_FONTS:
        f = load_font(name, FONT_SIZE)
        if f:
            fonts[name] = f
            print(f"Loaded: {name}")
        else:
            print(f"MISSING: {name}")

    if not fonts:
        print("ERROR: No fonts loaded!")
        sys.exit(1)

    n_fonts = len(fonts)
    n_cols = 4  # 3 light colors + 1 dark

    # Canvas size
    canvas_w = LABEL_W + n_cols * (CELL_W + GAP) + GAP
    canvas_h = HEADER_H + n_fonts * (CELL_H + GAP) + GAP + 30
    canvas = Image.new("RGB", (canvas_w, canvas_h), "#f0f0f0")
    draw = ImageDraw.Draw(canvas)

    # Cat reference at top left
    cat_img = auto_crop_alpha(Image.open(SOURCE_IMG))
    cat_size = 180
    cat_thumb = cat_img.resize((cat_size, cat_size), Image.LANCZOS)
    cat_x = 40
    cat_y = 30
    canvas.paste(cat_thumb, (cat_x, cat_y), cat_thumb)

    # Title
    try:
        title_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 36)
        subtitle_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeui.ttf"), 22)
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    draw.text((cat_x + cat_size + 30, cat_y + 20), "CatWing Logo — Font Samples", font=title_font, fill="#1a1a2e")
    draw.text(
        (cat_x + cat_size + 30, cat_y + 70),
        'Casing: "CatWing" (PascalCase)  |  Pick your font + color combo',
        font=subtitle_font, fill="#555555",
    )
    draw.text(
        (cat_x + cat_size + 30, cat_y + 100),
        "Light bg shows all 3 color options  |  Dark bg uses white text",
        font=subtitle_font, fill="#555555",
    )

    # Column headers
    header_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 20)
    header_y = HEADER_H - 50
    col_labels = [
        f"charcoal {LIGHT_COLORS[0][0]}",
        f"blue {LIGHT_COLORS[1][0]}",
        f"teal {LIGHT_COLORS[2][0]}",
        f"dark bg {BG_DARK}",
    ]
    for ci, label in enumerate(col_labels):
        cx = LABEL_W + ci * (CELL_W + GAP) + GAP + CELL_W // 2
        bbox = header_font.getbbox(label)
        lw = bbox[2] - bbox[0]
        color = LIGHT_COLORS[ci][0] if ci < 3 else "#ffffff"
        # Draw a small color swatch
        sw = 16
        sy = header_y + 2
        sx = cx - lw // 2 - sw - 8
        if ci < 3:
            draw.rectangle([sx, sy, sx + sw, sy + sw], fill=LIGHT_COLORS[ci][0])
        else:
            draw.rectangle([sx, sy, sx + sw, sy + sw], fill=BG_DARK, outline="#999999")
        draw.text((cx - lw // 2, header_y), label, font=header_font, fill="#333333")

    # Row label fonts
    label_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 20)
    desc_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeui.ttf"), 16)

    # Render grid
    for fi, (font_name, font) in enumerate(fonts.items()):
        row_y = HEADER_H + fi * (CELL_H + GAP) + GAP

        # Font name + description
        desc = GOOGLE_FONTS[font_name].get("desc", "")
        draw.text((14, row_y + 20), font_name, font=label_font, fill="#222222")
        draw.text((14, row_y + 48), desc, font=desc_font, fill="#777777")

        # Row number
        num_font = ImageFont.truetype(str(WIN_FONT_DIR / "segoeuib.ttf"), 28)
        draw.text((LABEL_W - 40, row_y + 50), str(fi + 1), font=num_font, fill="#bbbbbb")

        # 3 light-bg cells (one per color)
        for ci, (color_hex, _) in enumerate(LIGHT_COLORS):
            cell = render_cell(TEXT, font, BG_LIGHT, color_hex)
            cx = LABEL_W + ci * (CELL_W + GAP) + GAP
            canvas.paste(cell, (cx, row_y))

        # 1 dark-bg cell
        cell_dark = render_cell(TEXT, font, BG_DARK, TEXT_COLOR_DARK)
        cx = LABEL_W + 3 * (CELL_W + GAP) + GAP
        canvas.paste(cell_dark, (cx, row_y))

    # Save
    canvas.save(OUTPUT_FILE, "PNG")
    print(f"\nSaved: {OUTPUT_FILE} ({canvas_w}x{canvas_h})")

    # Auto-open
    os.startfile(str(OUTPUT_FILE))


if __name__ == "__main__":
    main()
