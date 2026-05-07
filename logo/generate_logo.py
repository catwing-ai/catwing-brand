"""
Phase 2: Generate final CatWing logo set with wordmark.

Configure CHOSEN_* constants below based on Phase 1 sample sheet selection,
then run:
    cd D:/_projects/__CAT_WING/logo
    python generate_logo.py

Output goes to logo/output/ — original files are untouched.
"""

import base64
import os
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# USER CONFIG — Set these after reviewing samples.png
# ---------------------------------------------------------------------------
# Font: one of the names from generate_samples.py
CHOSEN_FONT = "Outfit Bold"

# Casing: "CatWing" | "CATWING" | "catwing"
CHOSEN_CASING = "CatWing"

# Text color (on light/transparent bg): "#1a1a2e" | "#3064b6" | "#20b0a5"
CHOSEN_COLOR = "#1a1a2e"

# Dark bg color
DARK_BG = "#0f1923"
DARK_TEXT = "#ffffff"

# Letter-spacing (extra px between chars at reference size)
LETTER_SPACING_REF = 4  # at 100pt font size, scales proportionally

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
FONTS_DIR = SCRIPT_DIR / "fonts"
# Use AI-upscaled 4800px source for maximum quality; fall back to 1200px
SOURCE_IMG_HQ = SCRIPT_DIR / "catwing_logo_4800x4800.png"
SOURCE_IMG_ORIG = SCRIPT_DIR / "catwing_logo_1200x1200.png"
SOURCE_IMG = SOURCE_IMG_HQ if SOURCE_IMG_HQ.exists() else SOURCE_IMG_ORIG
OUTPUT_DIR = SCRIPT_DIR / "output"
WIN_FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"

# Font registry
GOOGLE_FONTS = {
    "Outfit Bold": {
        "file": "Outfit-Variable.ttf",
        "variation": 700,
    },
    "Sora SemiBold": {
        "file": "Sora-Variable.ttf",
        "variation": 600,
    },
}

SYSTEM_FONTS = {}


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------
def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load font by name. Raises if unavailable."""
    if name in GOOGLE_FONTS:
        info = GOOGLE_FONTS[name]
        path = FONTS_DIR / info["file"]
        font = ImageFont.truetype(str(path), size)
        if info.get("variation") and hasattr(font, "set_variation_by_axes"):
            axes = font.get_variation_axes()
            axis_values = [
                info["variation"] if ax["name"] == b"wght" else ax.get("default", ax["minimum"])
                for ax in axes
            ]
            font.set_variation_by_axes(axis_values)
        return font

    if name in SYSTEM_FONTS:
        filename, variation = SYSTEM_FONTS[name]
        path = WIN_FONT_DIR / filename
        if not path.exists():
            path = WIN_FONT_DIR / filename.lower()
        font = ImageFont.truetype(str(path), size)
        if variation and hasattr(font, "set_variation_by_axes"):
            try:
                font.set_variation_by_axes([variation])
            except Exception:
                pass
        return font

    raise ValueError(f"Unknown font: {name}")


def get_font_path(name: str) -> Path:
    """Get the file path to a font."""
    if name in GOOGLE_FONTS:
        return FONTS_DIR / GOOGLE_FONTS[name]["file"]
    if name in SYSTEM_FONTS:
        filename, _ = SYSTEM_FONTS[name]
        path = WIN_FONT_DIR / filename
        return path if path.exists() else WIN_FONT_DIR / filename.lower()
    raise ValueError(f"Unknown font: {name}")


# ---------------------------------------------------------------------------
# Text rendering helpers
# ---------------------------------------------------------------------------
def scaled_spacing(font_size: int) -> int:
    """Scale letter-spacing proportionally to font size."""
    return max(1, round(LETTER_SPACING_REF * font_size / 100))


def measure_text_spaced(font: ImageFont.FreeTypeFont, text: str, spacing: int) -> tuple[int, int]:
    """Return (width, height) of spaced text using getbbox()."""
    if not text:
        return (0, 0)
    total_w = 0
    max_h = 0
    for i, ch in enumerate(text):
        bbox = font.getbbox(ch)
        ch_w = bbox[2] - bbox[0]
        ch_h = bbox[3] - bbox[1]
        total_w += ch_w
        max_h = max(max_h, ch_h)
        if i < len(text) - 1:
            total_w += spacing
    # Get proper ascent for vertical positioning
    bbox_full = font.getbbox(text)
    return (total_w, bbox_full[3] - bbox_full[1])


def draw_text_spaced(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill,
    spacing: int,
):
    """Draw text char-by-char with letter-spacing."""
    x, y = pos
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        bbox = font.getbbox(ch)
        x += (bbox[2] - bbox[0]) + spacing


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
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


def img_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    """Convert PIL image to base64 data URI."""
    buf = BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def font_to_base64(font_path: Path) -> str:
    """Read font file and return base64 string."""
    return base64.b64encode(font_path.read_bytes()).decode("ascii")


def hex_to_rgba(hex_color: str) -> tuple[int, int, int, int]:
    """Convert hex color to RGBA tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)


# ---------------------------------------------------------------------------
# Logo composition
# ---------------------------------------------------------------------------
def compose_vertical(
    cat: Image.Image,
    text: str,
    font_name: str,
    text_color,
    bg_color: tuple | None = None,
    target_h: int = 1200,
) -> Image.Image:
    """
    Compose vertical logo: cat above, text below.
    ~6:7 aspect ratio. bg_color=None means transparent.
    """
    # Cat takes ~75% of height, text ~15%, gaps ~10%
    cat_h = int(target_h * 0.72)
    cat_w = int(cat.width * cat_h / cat.height)

    cat_resized = cat.resize((cat_w, cat_h), Image.LANCZOS)

    # Size the font to look good relative to cat width (~60% of cat width for text)
    # Try font sizes to find one that makes text ~55-65% of cat width
    target_text_w = int(cat_w * 0.85)
    font_size = 10
    while font_size < 500:
        test_font = load_font(font_name, font_size)
        sp = scaled_spacing(font_size)
        tw, _ = measure_text_spaced(test_font, text, sp)
        if tw >= target_text_w:
            break
        font_size += 1

    font = load_font(font_name, font_size)
    sp = scaled_spacing(font_size)
    tw, th = measure_text_spaced(font, text, sp)

    # Canvas dimensions
    gap = int(target_h * 0.04)  # gap between cat and text
    pad_top = int(target_h * 0.03)
    pad_bottom = int(target_h * 0.05)
    total_h = pad_top + cat_h + gap + th + pad_bottom
    canvas_w = max(cat_w, tw) + int(target_h * 0.06)  # side padding

    if bg_color:
        canvas = Image.new("RGBA", (canvas_w, total_h), bg_color)
    else:
        canvas = Image.new("RGBA", (canvas_w, total_h), (0, 0, 0, 0))

    # Center cat
    cx = (canvas_w - cat_w) // 2
    canvas.paste(cat_resized, (cx, pad_top), cat_resized)

    # Draw text centered below cat
    draw = ImageDraw.Draw(canvas)
    tx = (canvas_w - tw) // 2
    ty = pad_top + cat_h + gap
    # Adjust for font ascent offset
    bbox_ref = font.getbbox(text)
    ty -= bbox_ref[1]  # compensate for top bearing
    draw_text_spaced(draw, (tx, ty), text, font, text_color, sp)

    return canvas


def compose_horizontal(
    cat: Image.Image,
    text: str,
    font_name: str,
    text_color,
    bg_color: tuple | None = None,
    target_w: int = 800,
    target_h: int = 400,
) -> Image.Image:
    """Compose horizontal logo: cat left, text right. ~2:1 aspect."""
    # Cat fits within left portion
    cat_area_w = int(target_h * 0.85)
    cat_h = int(target_h * 0.75)
    cat_w = int(cat.width * cat_h / cat.height)
    cat_resized = cat.resize((cat_w, cat_h), Image.LANCZOS)

    # Font size: text height ~35% of canvas height
    target_text_h = int(target_h * 0.18)
    font_size = 10
    while font_size < 300:
        test_font = load_font(font_name, font_size)
        _, th = measure_text_spaced(test_font, text, scaled_spacing(font_size))
        if th >= target_text_h:
            break
        font_size += 1

    font = load_font(font_name, font_size)
    sp = scaled_spacing(font_size)
    tw, th = measure_text_spaced(font, text, sp)

    # Ensure canvas is wide enough
    gap = int(target_h * 0.08)
    pad_x = int(target_h * 0.06)
    needed_w = pad_x + cat_w + gap + tw + pad_x
    canvas_w = max(target_w, needed_w)

    if bg_color:
        canvas = Image.new("RGBA", (canvas_w, target_h), bg_color)
    else:
        canvas = Image.new("RGBA", (canvas_w, target_h), (0, 0, 0, 0))

    # Cat vertically centered on left
    cy = (target_h - cat_h) // 2
    canvas.paste(cat_resized, (pad_x, cy), cat_resized)

    # Text vertically centered to the right of cat
    draw = ImageDraw.Draw(canvas)
    tx = pad_x + cat_w + gap
    bbox_ref = font.getbbox(text)
    ty = (target_h - th) // 2 - bbox_ref[1]
    draw_text_spaced(draw, (tx, ty), text, font, text_color, sp)

    return canvas


def compose_wordmark(
    text: str,
    font_name: str,
    text_color,
    bg_color: tuple | None = None,
    target_w: int = 600,
) -> Image.Image:
    """Wordmark only (no cat)."""
    # Size font to fill ~80% of target width
    font_size = 10
    while font_size < 500:
        test_font = load_font(font_name, font_size)
        tw, _ = measure_text_spaced(test_font, text, scaled_spacing(font_size))
        if tw >= target_w * 0.8:
            break
        font_size += 1

    font = load_font(font_name, font_size)
    sp = scaled_spacing(font_size)
    tw, th = measure_text_spaced(font, text, sp)

    pad = int(th * 0.5)
    canvas_w = tw + pad * 2
    canvas_h = th + pad * 2

    if bg_color:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), bg_color)
    else:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    draw = ImageDraw.Draw(canvas)
    bbox_ref = font.getbbox(text)
    tx = (canvas_w - tw) // 2
    ty = pad - bbox_ref[1]
    draw_text_spaced(draw, (tx, ty), text, font, text_color, sp)

    return canvas


# ---------------------------------------------------------------------------
# SVG generation
# ---------------------------------------------------------------------------
def generate_svg(
    cat: Image.Image,
    text: str,
    font_name: str,
    text_color_hex: str,
    font_path: Path,
) -> str:
    """
    Generate self-contained SVG: full-res base64 PNG cat + embedded @font-face + vector <text>.
    The cat is embedded at native resolution (no downscaling) so zooming stays crisp
    up to the source pixel limit. Text is true vector and scales infinitely.
    """
    # Layout at a logical coordinate system
    target_h = 1200
    cat_h = int(target_h * 0.72)
    cat_w = int(cat.width * cat_h / cat.height)

    # Find font size
    target_text_w = int(cat_w * 0.85)
    font_size = 10
    while font_size < 500:
        test_font = load_font(font_name, font_size)
        sp = scaled_spacing(font_size)
        tw, _ = measure_text_spaced(test_font, text, sp)
        if tw >= target_text_w:
            break
        font_size += 1

    font = load_font(font_name, font_size)
    sp = scaled_spacing(font_size)
    tw, th = measure_text_spaced(font, text, sp)

    gap = int(target_h * 0.04)
    pad_top = int(target_h * 0.03)
    pad_bottom = int(target_h * 0.05)
    total_h = pad_top + cat_h + gap + th + pad_bottom
    canvas_w = max(cat_w, tw) + int(target_h * 0.06)

    # Embed cat at high resolution (cap at 2400px to keep SVG < 5MB)
    # SVG width/height handle visual sizing; extra pixels give zoom headroom
    svg_cat_max = 2400
    if max(cat.width, cat.height) > svg_cat_max:
        scale = svg_cat_max / max(cat.width, cat.height)
        svg_cat = cat.resize((int(cat.width * scale), int(cat.height * scale)), Image.LANCZOS)
    else:
        svg_cat = cat
    cat_b64 = img_to_base64(svg_cat)

    # Base64 encode font
    font_b64 = font_to_base64(font_path)
    font_ext = font_path.suffix.lower()
    font_format = "opentype" if font_ext == ".otf" else "truetype"
    font_mime = "font/otf" if font_ext == ".otf" else "font/ttf"

    svg_font_family = font_name.replace(" ", "")

    cat_x = (canvas_w - cat_w) // 2
    cat_y = pad_top
    text_x = canvas_w // 2
    text_y = pad_top + cat_h + gap + th // 2
    svg_letter_spacing = f"{sp / font_size:.3f}em"

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {canvas_w} {total_h}" width="{canvas_w}" height="{total_h}">
  <defs>
    <style>
      @font-face {{
        font-family: '{svg_font_family}';
        src: url('data:{font_mime};base64,{font_b64}') format('{font_format}');
        font-weight: 700;
        font-style: normal;
      }}
    </style>
  </defs>
  <image x="{cat_x}" y="{cat_y}" width="{cat_w}" height="{cat_h}"
         href="data:image/png;base64,{cat_b64}"
         image-rendering="optimizeQuality" />
  <text x="{text_x}" y="{text_y}"
        font-family="'{svg_font_family}', sans-serif"
        font-size="{font_size}" font-weight="700"
        fill="{text_color_hex}"
        text-anchor="middle" dominant-baseline="central"
        letter-spacing="{svg_letter_spacing}">{text}</text>
</svg>"""
    return svg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load and auto-crop source cat
    print("Loading source image...")
    cat_raw = Image.open(SOURCE_IMG).convert("RGBA")
    cat = auto_crop_alpha(cat_raw)
    print(f"  Auto-cropped: {cat_raw.size} -> {cat.size}")

    text = CHOSEN_CASING
    color_rgba = hex_to_rgba(CHOSEN_COLOR)
    dark_bg_rgba = hex_to_rgba(DARK_BG)
    dark_text_rgba = hex_to_rgba(DARK_TEXT)

    # --- Vertical logos (transparent bg) ---
    print("Generating vertical logos...")
    for size in [1200, 600, 300]:
        img = compose_vertical(cat, text, CHOSEN_FONT, color_rgba, target_h=size)
        path = OUTPUT_DIR / f"catwing_full_{size}.png"
        img.save(path, "PNG")
        print(f"  {path.name} ({img.width}x{img.height})")

    # --- Vertical dark variants ---
    print("Generating dark vertical logos...")
    for size in [1200, 600, 300]:
        img = compose_vertical(cat, text, CHOSEN_FONT, dark_text_rgba, bg_color=dark_bg_rgba, target_h=size)
        path = OUTPUT_DIR / f"catwing_full_dark_{size}.png"
        img.save(path, "PNG")
        print(f"  {path.name} ({img.width}x{img.height})")

    # --- Horizontal logos ---
    print("Generating horizontal logos...")
    img_h = compose_horizontal(cat, text, CHOSEN_FONT, color_rgba, target_w=800, target_h=400)
    img_h.save(OUTPUT_DIR / "catwing_horiz_800x400.png", "PNG")
    print(f"  catwing_horiz_800x400.png ({img_h.width}x{img_h.height})")

    img_hd = compose_horizontal(cat, text, CHOSEN_FONT, dark_text_rgba, bg_color=dark_bg_rgba, target_w=800, target_h=400)
    img_hd.save(OUTPUT_DIR / "catwing_horiz_dark_800x400.png", "PNG")
    print(f"  catwing_horiz_dark_800x400.png ({img_hd.width}x{img_hd.height})")

    # --- Icon only (cat, square) ---
    print("Generating icons...")
    for size in [256, 128, 64, 48]:
        icon = cat.resize((size, size), Image.LANCZOS)
        path = OUTPUT_DIR / f"catwing_icon_{size}.png"
        icon.save(path, "PNG")
        print(f"  {path.name}")

    # ICO (multi-size) — Pillow requires all sizes passed via append_images
    # and the base image should be the largest size
    ico_sizes = [256, 128, 64, 48, 32, 16]
    ico_images = [cat.resize((s, s), Image.LANCZOS) for s in ico_sizes]
    ico_path = OUTPUT_DIR / "catwing_icon.ico"
    ico_images[0].save(
        ico_path,
        format="ICO",
        append_images=ico_images[1:],
    )
    print(f"  catwing_icon.ico ({', '.join(str(s) for s in ico_sizes)})")

    # --- Wordmark only ---
    print("Generating wordmark...")
    wm = compose_wordmark(text, CHOSEN_FONT, color_rgba, target_w=600)
    wm.save(OUTPUT_DIR / "catwing_wordmark_600.png", "PNG")
    print(f"  catwing_wordmark_600.png ({wm.width}x{wm.height})")

    # --- SVG (full-res raster cat + vector text with embedded font) ---
    print("Generating SVG...")
    font_path = get_font_path(CHOSEN_FONT)
    svg_content = generate_svg(cat, text, CHOSEN_FONT, CHOSEN_COLOR, font_path)
    svg_path = OUTPUT_DIR / "catwing_full.svg"
    svg_path.write_text(svg_content, encoding="utf-8")
    svg_size_kb = svg_path.stat().st_size / 1024
    print(f"  catwing_full.svg ({svg_size_kb:.0f} KB)")

    # --- Summary ---
    print(f"\nAll files saved to: {OUTPUT_DIR}")
    files = sorted(OUTPUT_DIR.glob("*"))
    for f in files:
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:40s} {size_kb:8.1f} KB")

    print(f"\nConfig: font={CHOSEN_FONT}, casing={CHOSEN_CASING}, color={CHOSEN_COLOR}")


if __name__ == "__main__":
    main()
