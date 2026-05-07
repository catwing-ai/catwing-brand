"""Build the CatWing Documentation Wiki as self-contained HTML pages.

Usage:
    cd <repo>
    python tools/build.py [--fresh-fonts] [--no-open]

Outputs:
    index.html       Home page (wiki landing)
    brand.html       Brand Identity Guide
    design.html      UI & App Design Guide
    resources.html   Resources & Templates
"""

from __future__ import annotations

import argparse
import base64
import re
import urllib.request
import webbrowser
from datetime import date
from pathlib import Path

VERSION = "2.0"
BRAND_DIR = Path(__file__).resolve().parents[1]
PAGES = {
    "home": BRAND_DIR / "index.html",
    "brand": BRAND_DIR / "brand.html",
    "design": BRAND_DIR / "design.html",
    "resources": BRAND_DIR / "resources.html",
}
FONT_CACHE = BRAND_DIR / ".fonts"

# ── Asset Resolution ──────────────────────────────────────────────────────
# All assets resolve from logo/ in this repo. The two `streamlit_*` files are
# bundled copies of catwing_app/streamlit_apps/assortment_review/static/img/
# so the build is self-contained.

LOGO_DIR_KEYS = {
    "icon": "streamlit_logo.png",
    "favicon": "streamlit_favicon.ico",
    "icon_128": "catwing_icon_128.png",
    "full_light": "catwing_full_600.png",
    "full_dark": "catwing_full_dark_600.png",
    "horiz_light": "catwing_horiz_800x400.png",
    "horiz_dark": "catwing_horiz_dark_800x400.png",
    "wordmark": "catwing_wordmark_600.png",
    "favicon_ico": "catwing_icon.ico",
}


# ── Brand Data ────────────────────────────────────────────────────────────

COLORS = {
    "CW Blue": {
        "hex": "#336699",
        "role": "Primary brand, headers, table backgrounds",
        "group": "primary",
    },
    "CW Teal": {
        "hex": "#20b0a5",
        "role": "Accent, CTAs, secondary brand element",
        "group": "primary",
    },
    "CW Presentation Teal": {
        "hex": "#27C4CC",
        "role": "PPTX wordmark accent (lighter variant)",
        "group": "primary",
    },
    "CW Dark": {
        "hex": "#1c1c1c",
        "role": "Body text",
        "group": "primary",
    },
    "CW Background": {
        "hex": "#f5f7fa",
        "role": "Page backgrounds",
        "group": "primary",
    },
    "Logo Charcoal": {
        "hex": "#1a1a2e",
        "role": "Logo on light backgrounds",
        "group": "primary",
    },
    "Dark Mode BG": {
        "hex": "#0f1923",
        "role": "Dark surfaces",
        "group": "primary",
    },
    "Success": {
        "hex": "#4CAF50",
        "role": "Positive status, confirmations",
        "group": "semantic",
    },
    "Error": {
        "hex": "#D32F2F",
        "role": "Negative status, danger actions",
        "group": "semantic",
    },
    "Warning": {
        "hex": "#FF9800",
        "role": "Drift indicators, caution states",
        "group": "semantic",
    },
    "Amber": {
        "hex": "#FFC107",
        "role": "Zone indicators, attention",
        "group": "semantic",
    },
    "Blue": {
        "hex": "#42A5F5",
        "role": "Data visualization primary",
        "group": "dataviz",
    },
    "Green": {
        "hex": "#27AE60",
        "role": "Data visualization secondary",
        "group": "dataviz",
    },
    "Red": {
        "hex": "#C0392B",
        "role": "Data visualization alert",
        "group": "dataviz",
    },
    "Amber DV": {
        "hex": "#F39C12",
        "role": "Data visualization warm",
        "group": "dataviz",
    },
    "Teal DV": {
        "hex": "#17A589",
        "role": "Data visualization cool",
        "group": "dataviz",
    },
    "Purple": {
        "hex": "#8E44AD",
        "role": "Data visualization categorical",
        "group": "dataviz",
    },
}

TINTS = {
    "Confirmed": {"bg": "#E8F5E9", "border": "#4CAF50", "text": "#2E7D32"},
    "Drift": {"bg": "#FFF3E0", "border": "#FF9800", "text": "#BF360C"},
    "Danger": {"bg": "#FFEBEE", "border": "#D32F2F", "text": "#B71C1C"},
    "Info": {"bg": "#E3F2FD", "border": "#42A5F5", "text": "#1565C0"},
    "Launch": {"bg": "#E8F5E9", "text": "#2E7D32"},
    "Discontinued": {"bg": "#ECEFF1", "text": "#616161"},
    "Old": {"bg": "#FFEBEE", "text": "#C62828"},
    "Gold": {"bg": "#FFF8E1", "text": "#BF360C"},
}

GRADIENTS = {
    "Brand": {
        "css": "linear-gradient(135deg, #336699 0%, #20b0a5 100%)",
        "note": "Always 135deg. Headers, buttons, hero sections.",
    },
    "Sidebar": {
        "css": "linear-gradient(180deg, #f0f5fc 0%, #e8f0f7 100%)",
        "note": "Always vertical. Sidebar backgrounds only.",
    },
}

# ── Context-Specific Palettes ────────────────────────────────────────────
# Website: dark theme, vivid colors, gradient headers → for impact
# Admin: light theme, muted colors, solid headers → for 8hr daily use

ADMIN_COLORS = {
    "header_bg": "#336699",
    "stock": "#3d8b52",
    "notstock": "#c85a54",
    "warning": "#c98a2d",
    "info": "#4a7fb5",
}

WEBSITE_COLORS = {
    "header_bg": "linear-gradient(135deg, #336699 0%, #20b0a5 100%)",
    "stock": "#4CAF50",
    "notstock": "#D32F2F",
    "warning": "#FF9800",
    "info": "#42A5F5",
}

TYPE_SCALE = [
    ("Display", "2.4rem", "700", "Login title, hero headings"),
    ("H1", "1.5rem", "700", "Page headings, app header"),
    ("H2", "1.1rem", "600", "Section headings, detail panel titles"),
    ("Body", "1rem (14px)", "400", "Default text, paragraphs"),
    ("Small", "0.85rem", "500", "Table cells, form labels, sidebar text"),
    ("Caption", "0.75rem", "500", "Status card labels, footer text"),
    ("Badge", "0.78rem", "600", "Status badges, product labels"),
]


# ── Helpers ───────────────────────────────────────────────────────────────


def _image_to_b64(path: Path) -> str | None:
    if not path.exists():
        return None
    mime = "image/png"
    if path.suffix == ".ico":
        mime = "image/x-icon"
    elif path.suffix == ".svg":
        mime = "image/svg+xml"
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def _load_assets() -> dict[str, str | None]:
    assets: dict[str, str | None] = {}
    logo_dir = BRAND_DIR / "logo"
    if logo_dir.is_dir():
        for key, fname in LOGO_DIR_KEYS.items():
            p = logo_dir / fname
            uri = _image_to_b64(p)
            if uri:
                print(f"  Logo  [{key}]: {fname}")
            else:
                print(f"  Logo  [{key}]: NOT FOUND ({fname})")
            assets[key] = uri
    else:
        print(f"  Logo dir not found: {logo_dir}")
        for key in LOGO_DIR_KEYS:
            assets[key] = None
    return assets


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex_to_hsl(h: str) -> tuple[int, int, int]:
    r, g, b = (x / 255 for x in _hex_to_rgb(h))
    mx, mn = max(r, g, b), min(r, g, b)
    lum = (mx + mn) / 2
    if mx == mn:
        hue = sat = 0
    else:
        d = mx - mn
        sat = d / (2 - mx - mn) if lum > 0.5 else d / (mx + mn)
        if mx == r:
            hue = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            hue = (b - r) / d + 2
        else:
            hue = (r - g) / d + 4
        hue /= 6
    return round(hue * 360), round(sat * 100), round(lum * 100)


def _wcag_luminance(h: str) -> float:
    r, g, b = _hex_to_rgb(h)
    vals = []
    for c in (r, g, b):
        c /= 255
        vals.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def _contrast_ratio(c1: str, c2: str) -> float:
    l1 = _wcag_luminance(c1) + 0.05
    l2 = _wcag_luminance(c2) + 0.05
    return max(l1, l2) / min(l1, l2)


def _fetch_and_embed_fonts(fresh: bool = False) -> str:
    FONT_CACHE.mkdir(exist_ok=True)
    families = [
        "Poppins:wght@400;500;600;700",
        "Outfit:wght@700",
    ]
    params = "&".join(f"family={f}" for f in families)
    url = f"https://fonts.googleapis.com/css2?{params}&display=swap"

    cache_file = FONT_CACHE / "fonts.css"
    if cache_file.exists() and not fresh:
        print("  Fonts: using cached CSS")
        return cache_file.read_text(encoding="utf-8")

    print("  Fonts: downloading from Google Fonts...")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            css_text = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  Fonts: download failed ({e}), using CDN fallback")
        return ""

    def _replace_url(match: re.Match) -> str:
        font_url = match.group(1)
        fname = font_url.split("/")[-1]
        local = FONT_CACHE / fname
        if local.exists() and not fresh:
            data = local.read_bytes()
        else:
            try:
                with urllib.request.urlopen(font_url, timeout=15) as r:
                    data = r.read()
                local.write_bytes(data)
            except Exception:
                return match.group(0)
        b64 = base64.b64encode(data).decode("ascii")
        return f"url(data:font/woff2;base64,{b64})"

    embedded = re.sub(r"url\((https://[^)]+\.woff2)\)", _replace_url, css_text)
    cache_file.write_text(embedded, encoding="utf-8")
    print(f"  Fonts: cached to {cache_file.name}")
    return embedded


# ── Section Builders ──────────────────────────────────────────────────────


def _sec_cover(assets: dict) -> str:
    logo_img = ""
    if assets["icon"]:
        logo_img = f'<img src="{assets["icon"]}" alt="CatWing" class="hero-logo">'
    else:
        logo_img = '<div class="hero-logo-placeholder">CW</div>'

    return f"""
    <section id="cover" class="hero">
      <div class="hero-inner">
        {logo_img}
        <h1>CatWing</h1>
        <p class="hero-tagline">Deep-tech AI for Supply Chain Optimization</p>
        <p class="hero-sub">Brand Identity Guidelines &mdash; v{VERSION} &middot; {date.today().strftime("%B %Y")}</p>
      </div>
    </section>"""


def _sec_philosophy() -> str:
    return """
    <section id="philosophy">
      <h2>2. Brand Philosophy</h2>

      <h3>Core Positioning</h3>
      <p><strong>CatWing is the infrastructure layer for intelligent inventory.</strong>
      We transform raw supply chain data into precise, actionable decisions.
      Every pixel in our interface exists to help analysts make better choices faster.</p>

      <h3>Personality Pillars</h3>
      <div class="pillar-grid">
        <div class="pillar-card">
          <h4>Precise</h4>
          <p>Numbers are right-aligned with tabular-nums. Dates follow consistent formatting.
          Every data point is verifiable.</p>
          <div class="pillar-example">Product: &euro;12,450 revenue, tabular-nums, right-aligned</div>
        </div>
        <div class="pillar-card">
          <h4>Opinionated</h4>
          <p>CW Rec status takes a clear position. We recommend STOCK or NOT-STOCK, never
          &ldquo;maybe&rdquo;. Confidence scores quantify uncertainty rather than hiding it.</p>
          <div class="pillar-example">Product: CW Rec = NOT-STOCK (dead score 87/100)</div>
        </div>
        <div class="pillar-card">
          <h4>Quiet</h4>
          <p>Animations are 0.15s-0.3s, never bouncing. Toasts dismiss themselves. Color is
          semantic only. The UI stays out of the way until you need it.</p>
          <div class="pillar-example">Toast: &ldquo;Changes saved&rdquo; &mdash; auto-dismiss, no fanfare</div>
        </div>
        <div class="pillar-card">
          <h4>Technical</h4>
          <p>We show confidence scores, not just recommendations. Monospace for data.
          Tables over cards. Numbers over charts. Density is a feature.</p>
          <div class="pillar-example">Confidence: 0.85 (Data 0.9, Demand 0.8, Recency 0.7)</div>
        </div>
        <div class="pillar-card">
          <h4>Trustworthy</h4>
          <p>Undo on every destructive action. 5-second recovery window. Drift detection
          alerts when recommendations change. No silent overwrites.</p>
          <div class="pillar-example">Toast: &ldquo;Status changed&rdquo; [Undo] &mdash; 5s window</div>
        </div>
      </div>

      <h3>This, Not That</h3>
      <div class="this-not-that">
        <div class="tnt-col this">
          <h4>CatWing is&hellip;</h4>
          <ul>
            <li>Deep-tech AI for supply chain professionals</li>
            <li>Information-dense, data-first interfaces</li>
            <li>Quiet confidence with semantic-only color</li>
            <li>Engineering-grade precision and credibility</li>
          </ul>
        </div>
        <div class="tnt-col that">
          <h4>CatWing is NOT&hellip;</h4>
          <ul>
            <li>Generic SaaS with playful illustrations</li>
            <li>Card-heavy dashboards with vanity metrics</li>
            <li>Decorative gradients and branded everything</li>
            <li>Enterprise grey with stock photography</li>
          </ul>
        </div>
      </div>

      <h3>Visual Identity &rarr; AI</h3>
      <ul>
        <li><strong>Gradient</strong> = data flow (blue inputs &rarr; teal outputs)</li>
        <li><strong>Monospace numbers</strong> = engineering credibility</li>
        <li><strong>Information density</strong> = AI processing power</li>
        <li><strong>Semantic-only color</strong> = no decoration, every hue means something</li>
      </ul>
    </section>"""


def _logo_card(
    src: str | None,
    caption: str,
    file_info: str,
    variant: str = "",
    img_style: str = "",
) -> str:
    """Render a single logo card.

    variant: "light" | "dark" | "" (default, uses guide theme)
    """
    cls = "logo-card"
    if variant == "light":
        cls += " logo-card-light"
    elif variant == "dark":
        cls += " logo-card-dark"

    if not src:
        return f"""
        <div class="{cls}">
          <div class="logo-display placeholder">{caption} not available</div>
          <p class="logo-caption">{caption}</p>
        </div>"""
    return f"""
        <div class="{cls}">
          <div class="logo-display"><img src="{src}" alt="{caption}" {f'style="{img_style}"' if img_style else ""}></div>
          <p class="logo-caption">{caption}</p>
          <p class="logo-file">{file_info}</p>
        </div>"""


def _sec_logos(assets: dict) -> str:
    # Icon variants
    icon_128 = assets.get("icon_128") or assets.get("icon")

    # Vertical (full) logos
    full_light = assets.get("full_light")
    full_dark = assets.get("full_dark")

    # Horizontal logos
    horiz_light = assets.get("horiz_light")
    horiz_dark = assets.get("horiz_dark")

    # Wordmark
    wordmark = assets.get("wordmark")

    # Favicon
    favicon = assets.get("favicon_ico") or assets.get("favicon")

    # ── Icon Mark ──
    icon_cards = _logo_card(
        icon_128,
        "Wing Icon Mark",
        "catwing_icon_128.png &mdash; 128&times;128px",
        variant="light",
    )
    icon_cards += _logo_card(
        favicon,
        "Favicon",
        "catwing_icon.ico &mdash; multi-size",
        variant="light",
        img_style="width:64px;height:64px;image-rendering:pixelated",
    )

    # ── Icon on Backgrounds ──
    bg_showcase = ""
    if icon_128:
        bg_showcase = f"""
      <h3>Icon on Backgrounds</h3>
      <div class="logo-bg-grid">
        <div class="logo-bg-cell logo-bg-white">
          <img src="{icon_128}" alt="Icon on white">
          <span class="logo-bg-label">White</span>
        </div>
        <div class="logo-bg-cell logo-bg-light">
          <img src="{icon_128}" alt="Icon on light">
          <span class="logo-bg-label">#f5f7fa</span>
        </div>
        <div class="logo-bg-cell logo-bg-dark">
          <img src="{icon_128}" alt="Icon on dark">
          <span class="logo-bg-label">#0f1923</span>
        </div>
        <div class="logo-bg-cell logo-bg-gradient">
          <img src="{icon_128}" alt="Icon on gradient">
          <span class="logo-bg-label">Brand gradient</span>
        </div>
      </div>
      <p class="note">The wing icon works on all backgrounds without modification.</p>"""

    # ── Vertical Lockup ──
    vert_html = ""
    if full_light or full_dark:
        vert_cards = ""
        if full_light:
            vert_cards += _logo_card(
                full_light,
                "Vertical &mdash; Light",
                "catwing_full_600.png",
                variant="light",
                img_style="max-width:240px;max-height:240px",
            )
        if full_dark:
            vert_cards += _logo_card(
                full_dark,
                "Vertical &mdash; Dark",
                "catwing_full_dark_600.png",
                variant="dark",
                img_style="max-width:240px;max-height:240px",
            )
        vert_html = f"""
      <h3>Vertical Lockup (Icon + Wordmark)</h3>
      <div class="logo-grid">{vert_cards}</div>
      <p class="note">Use vertical lockup when the logo is the primary focal point (title slides, splash screens, about pages).</p>"""

    # ── Horizontal Lockup ──
    horiz_html = ""
    if horiz_light or horiz_dark:
        horiz_cards = ""
        if horiz_light:
            horiz_cards += _logo_card(
                horiz_light,
                "Horizontal &mdash; Light",
                "catwing_horiz_800x400.png",
                variant="light",
                img_style="max-width:100%;max-height:200px",
            )
        if horiz_dark:
            horiz_cards += _logo_card(
                horiz_dark,
                "Horizontal &mdash; Dark",
                "catwing_horiz_dark_800x400.png",
                variant="dark",
                img_style="max-width:100%;max-height:200px",
            )
        horiz_html = f"""
      <h3>Horizontal Lockup (Icon + Wordmark)</h3>
      <div class="logo-grid logo-grid-wide">{horiz_cards}</div>
      <p class="note">Use horizontal lockup for headers, navigation bars, and inline placements.</p>"""

    # ── Wordmark Only ──
    wordmark_html = ""
    if wordmark:
        wordmark_html = f"""
      <h3>Wordmark Only</h3>
      <div class="logo-grid">
        {
            _logo_card(
                wordmark,
                "Wordmark &mdash; Light",
                "catwing_wordmark_600.png",
                variant="light",
                img_style="max-width:240px",
            )
        }
        <div class="logo-card logo-card-dark">
          <div class="logo-display"><img src="{
            wordmark
        }" alt="Wordmark on dark" style="max-width:240px;filter:brightness(0) invert(1)"></div>
          <p class="logo-caption">Wordmark &mdash; Dark (inverted)</p>
          <p class="logo-file">Use white text on dark backgrounds</p>
        </div>
      </div>
      <p class="note">Wordmark alone for tight spaces or when the icon is already visible nearby. Outfit Bold, charcoal #1a1a2e on light, white on dark.</p>"""

    return f"""
    <section id="logos">
      <h2>3. Logo System</h2>

      <h3>Icon Mark</h3>
      <p>The wing icon is the <strong>primary visual mark</strong> for CatWing.</p>
      <div class="logo-grid">
        {icon_cards}
      </div>
      {bg_showcase}

      {vert_html}
      {horiz_html}
      {wordmark_html}

      <h3>Construction Rules</h3>
      <ul>
        <li><strong>Typeface:</strong> Outfit Bold (700), PascalCase &ldquo;CatWing&rdquo;, letter-spacing 4px at 100pt</li>
        <li><strong>Clear space:</strong> Minimum = height of the &ldquo;C&rdquo; character on all sides</li>
        <li><strong>Minimum sizes:</strong> Icon 32px, horizontal lockup 120px width</li>
        <li><strong>Light text color:</strong> Charcoal #1a1a2e</li>
        <li><strong>Dark text color:</strong> White #ffffff</li>
      </ul>

      <h3>When to Use Each Variant</h3>
      <table class="spec-table">
        <thead><tr><th>Variant</th><th>Context</th><th>Min Size</th></tr></thead>
        <tbody>
          <tr><td><strong>Icon only</strong></td><td>Favicons, app headers, small UI elements</td><td>32px</td></tr>
          <tr><td><strong>Vertical lockup</strong></td><td>Title slides, splash screens, about pages</td><td>200px wide</td></tr>
          <tr><td><strong>Horizontal lockup</strong></td><td>Email signatures, document headers, nav bars</td><td>160px wide</td></tr>
          <tr><td><strong>Wordmark only</strong></td><td>When icon is already present nearby</td><td>120px wide</td></tr>
        </tbody>
      </table>

      <h3>Do&rsquo;s and Don&rsquo;ts</h3>
      <div class="dos-donts">
        <div class="do">
          <h4>Do</h4>
          <ul>
            <li>Use the wing icon at correct proportions</li>
            <li>Maintain clear space = height of the &ldquo;C&rdquo; on all sides</li>
            <li>Use dark variants on dark backgrounds</li>
            <li>Use icon-only at small sizes (&lt;120px)</li>
            <li>Apply the glow effect on brand gradient backgrounds</li>
          </ul>
        </div>
        <div class="dont">
          <h4>Don&rsquo;t</h4>
          <ul>
            <li>Stretch, skew, or rotate the logo</li>
            <li>Recolor with non-brand colors</li>
            <li>Place on busy or photographic backgrounds</li>
            <li>Add shadows, outlines, or effects (except brand glow)</li>
            <li>Use the light variant on dark surfaces (use dark variant)</li>
          </ul>
        </div>
      </div>

      <h3>File Formats</h3>
      <table class="spec-table">
        <thead><tr><th>Format</th><th>Sizes</th><th>Use Case</th></tr></thead>
        <tbody>
          <tr><td>PNG</td><td>48, 64, 128, 256px</td><td>Icon mark (web, favicons)</td></tr>
          <tr><td>PNG</td><td>300, 600, 1200px</td><td>Full lockup (presentations, documents)</td></tr>
          <tr><td>PNG</td><td>800&times;400px</td><td>Horizontal lockup (headers, sidebars)</td></tr>
          <tr><td>ICO</td><td>Multi-size</td><td>Browser favicon</td></tr>
          <tr><td>SVG</td><td>Vector</td><td>Full lockup (scalable, print)</td></tr>
        </tbody>
      </table>
    </section>"""


def _swatch_html(name: str, info: dict) -> str:
    h = info["hex"]
    r, g, b = _hex_to_rgb(h)
    hue, s, lum = _hex_to_hsl(h)
    # Use WCAG contrast ratio to pick text color (not HSL luminance)
    cr_white = _contrast_ratio(h, "#ffffff")
    cr_dark = _contrast_ratio(h, "#1c1c1c")
    text_color = "#fff" if cr_white >= cr_dark else "#1c1c1c"

    if cr_white < 4.5:
        aa_note = f'<span class="wcag-fail">vs white {cr_white:.1f}:1</span>'
    else:
        aa_note = f'<span class="wcag-pass">vs white {cr_white:.1f}:1</span>'

    return f"""
      <div class="swatch" title="Click to copy {h}">
        <div class="swatch-color" style="background:{h};color:{text_color}">
          <span class="swatch-hex">{h}</span>
        </div>
        <div class="swatch-info">
          <strong>{name}</strong>
          <span class="swatch-rgb">rgb({r}, {g}, {b})</span>
          <span class="swatch-hsl">hsl({hue}, {s}%, {lum}%)</span>
          <span class="swatch-role">{info["role"]}</span>
          {aa_note}
          <span class="copy-feedback"></span>
        </div>
      </div>"""


def _sec_colors() -> str:
    primary = [_swatch_html(n, i) for n, i in COLORS.items() if i["group"] == "primary"]
    semantic = [
        _swatch_html(n, i) for n, i in COLORS.items() if i["group"] == "semantic"
    ]
    dataviz = [_swatch_html(n, i) for n, i in COLORS.items() if i["group"] == "dataviz"]

    grad_html = ""
    for name, g in GRADIENTS.items():
        grad_html += f"""
        <div class="gradient-card">
          <div class="gradient-preview" style="background:{g["css"]}"></div>
          <div class="gradient-info">
            <strong>{name}</strong>
            <code>{g["css"]}</code>
            <span class="swatch-role">{g["note"]}</span>
          </div>
        </div>"""

    tint_html = ""
    for name, t in TINTS.items():
        border = t.get("border", t.get("text", "#ccc"))
        text = t.get("text", border)
        tint_html += f"""
        <div class="tint-chip" style="background:{t["bg"]};border-left:4px solid {border};color:{text}">
          {name} <code>{t["bg"]}</code>
        </div>"""

    # WCAG accessibility matrix
    fg_colors = [
        ("CW Blue #336699", "#336699"),
        ("CW Teal #20b0a5", "#20b0a5"),
        ("Pres. Teal #27C4CC", "#27C4CC"),
        ("Success #4CAF50", "#4CAF50"),
        ("Error #D32F2F", "#D32F2F"),
        ("CW Dark #1c1c1c", "#1c1c1c"),
    ]
    bg_colors = [
        ("White", "#ffffff"),
        ("CW BG #f5f7fa", "#f5f7fa"),
        ("Dark #0f1923", "#0f1923"),
        ("Surface #1a2332", "#1a2332"),
    ]
    wcag_rows = ""
    for fg_name, fg_hex in fg_colors:
        cells = f"<td><strong>{fg_name}</strong></td>"
        for _, bg_hex in bg_colors:
            cr = _contrast_ratio(fg_hex, bg_hex)
            cls = "pass" if cr >= 4.5 else "fail"
            label = "AA" if cr >= 4.5 else ("AA-lg" if cr >= 3.0 else "Fail")
            cells += f'<td class="{cls}">{cr:.1f}:1 {label}</td>'
        wcag_rows += f"<tr>{cells}</tr>"

    wcag_header = "<th>Foreground</th>"
    for bg_name, _ in bg_colors:
        wcag_header += f"<th>{bg_name}</th>"

    teal_cr = _contrast_ratio("#20b0a5", "#ffffff")
    blue_cr = _contrast_ratio("#336699", "#ffffff")

    return f"""
    <section id="colors">
      <h2>4. Color System</h2>

      <h3>Primary Palette</h3>
      <p class="note">Click any swatch to copy its hex code.</p>
      <div class="swatch-grid">{"".join(primary)}</div>

      <h3>Gradients</h3>
      <div class="gradient-grid">{grad_html}</div>

      <h3>Semantic Colors</h3>
      <div class="swatch-grid">{"".join(semantic)}</div>

      <h3>Data Visualization Palette</h3>
      <div class="swatch-grid">{"".join(dataviz)}</div>

      <h3>Background Tints</h3>
      <p class="note">Used for status row highlighting and product labels.</p>
      <div class="tint-grid">{tint_html}</div>

      <h3>WCAG Accessibility Matrix</h3>
      <table class="wcag-matrix">
        <thead><tr>{wcag_header}</tr></thead>
        <tbody>{wcag_rows}</tbody>
      </table>

      <div class="callout warning">
        <strong>CW Teal on white:</strong> {teal_cr:.1f}:1 &mdash; fails WCAG AA for body text.
        Restrict to large text (&ge;18px bold), icons, or use on colored backgrounds only.
      </div>
      <div class="callout info">
        <strong>CW Blue on white:</strong> {blue_cr:.1f}:1 &mdash; passes AA for large text.
        Safe for headings, table headers, and buttons.
      </div>

      <h3>Fragmentation Notes</h3>
      <div class="callout">
        Supplier analytics uses <code>#3cac34</code> for green vs status green <code>#4CAF50</code>.
        Recommend converging to <code>#4CAF50</code> across all apps.
      </div>

      <div class="callout">
        <strong>Context-specific palettes:</strong> These canonical colors are adapted for each deployment context.
        See the <a href="design.html">UI &amp; App Design Guide</a> for website (dark/vivid) and admin app (light/muted) variants.
      </div>
    </section>"""


def _sec_typography() -> str:
    scale_rows = ""
    for name, size, weight, usage in TYPE_SCALE:
        numeric = size.split("(")[0].strip()
        scale_rows += f"""
        <div class="type-row">
          <span class="type-sample" style="font-size:{numeric};font-weight:{weight}">{name}</span>
          <span class="type-spec">{size} / {weight}</span>
          <span class="type-usage">{usage}</span>
        </div>"""

    return f"""
    <section id="typography">
      <h2>5. Typography</h2>

      <h3>Font Pairing</h3>
      <table class="spec-table">
        <thead><tr><th>Context</th><th>Font</th><th>Weights</th></tr></thead>
        <tbody>
          <tr><td>Logo / wordmark</td><td style="font-family:Outfit,sans-serif;font-weight:700">Outfit Bold</td><td>700</td></tr>
          <tr><td>Web applications</td><td style="font-family:Poppins,sans-serif">Poppins</td><td>400, 500, 600, 700</td></tr>
          <tr><td>Presentations (body)</td><td>Roboto</td><td>400, 700</td></tr>
          <tr><td>Presentations (charts)</td><td>Calibri</td><td>400</td></tr>
          <tr><td>Code / data</td><td style="font-family:SFMono-Regular,Consolas,monospace">SFMono / Consolas</td><td>400 at 0.88em</td></tr>
        </tbody>
      </table>

      <h3>Type Scale</h3>
      <div class="type-scale">{scale_rows}</div>

      <h3>Line Height</h3>
      <table class="spec-table">
        <thead><tr><th>Context</th><th>Value</th></tr></thead>
        <tbody>
          <tr><td>Body text</td><td>1.6</td></tr>
          <tr><td>Tight (tables, badges)</td><td>1.4</td></tr>
          <tr><td>Headings</td><td>1.2</td></tr>
        </tbody>
      </table>

      <h3>Letter Spacing</h3>
      <ul>
        <li><strong>Logo wordmark:</strong> 4px at 100pt</li>
        <li><strong>Sidebar headings:</strong> 0.04em uppercase</li>
        <li><strong>Everything else:</strong> normal</li>
      </ul>

      <h3>Number Formatting</h3>
      <div class="number-demo">
        <span>&euro;12,450</span>
        <span>1,247</span>
        <span>95.8%</span>
      </div>
      <p class="spec">font-variant-numeric: tabular-nums &middot; right-aligned &middot; comma thousands &middot; &euro; prefix, no decimals for large values &middot; 1 decimal for percentages</p>

      <h3>Pairing Rules</h3>
      <ul>
        <li>Never use Outfit in body text &mdash; reserved for the wordmark</li>
        <li>Never use Poppins for the logo &mdash; always Outfit Bold</li>
        <li>Code blocks: <code>SFMono-Regular, Consolas, monospace</code> at 0.88em</li>
      </ul>

      <h3>Typography in Context</h3>
      <div class="type-context-demo">
        <div class="tc-card">
          <div class="tc-label">Page Header</div>
          <div style="font-size:1.5rem;font-weight:700;color:var(--guide-text);margin-bottom:0.2rem">Global Assortment Review</div>
          <div style="font-size:0.85rem;color:var(--guide-text-muted)">CW-200 &middot; Tissot &middot; 1,247 products &middot; Last updated 02 Mar 2026</div>
        </div>
        <div class="tc-card">
          <div class="tc-label">Table Cell Pairing</div>
          <div style="font-size:0.85rem;font-weight:600;color:var(--guide-text)">T-Sport XL Chrono</div>
          <div style="font-size:0.75rem;color:var(--guide-text-muted);font-variant-numeric:tabular-nums">T123.456.789 &middot; &euro;425 &middot; Zone A</div>
        </div>
        <div class="tc-card">
          <div class="tc-label">KPI Card</div>
          <div style="font-size:2rem;font-weight:700;color:#336699;font-variant-numeric:tabular-nums">&euro;2.4M</div>
          <div style="font-size:0.8rem;font-weight:500;color:var(--guide-text-muted)">Revenue Uplift (+12.3%)</div>
        </div>
        <div class="tc-card">
          <div class="tc-label">Form Label + Input</div>
          <div style="font-size:0.8rem;font-weight:600;color:var(--guide-text);margin-bottom:0.3rem">Notes</div>
          <div style="border:1px solid var(--guide-border);border-radius:6px;padding:0.4rem 0.6rem;font-size:0.85rem;color:var(--guide-text-muted)">Add review notes&hellip;</div>
        </div>
      </div>
    </section>"""


def _sec_iconography() -> str:
    return """
    <section id="iconography">
      <h2>6. Iconography</h2>

      <p>CatWing uses <strong>Unicode characters + CSS indicators</strong> rather than an icon library.
      This keeps the bundle minimal and ensures icons render without external dependencies.</p>

      <h3>Zone Dots</h3>
      <p class="note">The canonical micro-icon. 10px circles with semantic zone colors.</p>
      <div class="zone-dots-demo">
        <div class="zone-dot-sample"><span class="dot" style="background:#4CAF50"></span> A (Green)</div>
        <div class="zone-dot-sample"><span class="dot" style="background:#FFC107"></span> B (Yellow)</div>
        <div class="zone-dot-sample"><span class="dot" style="background:#FF9800"></span> C (Orange)</div>
        <div class="zone-dot-sample"><span class="dot" style="background:#D32F2F"></span> D (Red)</div>
      </div>

      <h3>Status Indicators</h3>
      <div class="icon-grid">
        <div class="icon-card">
          <div class="icon-demo" style="color:#4CAF50">&#10003;</div>
          <div class="icon-label">Confirmed</div>
        </div>
        <div class="icon-card">
          <div class="icon-demo" style="color:#FF9800">&#9888;</div>
          <div class="icon-label">Drift / Re-review</div>
        </div>
        <div class="icon-card">
          <div class="icon-demo" style="color:#aaa">&#128274;</div>
          <div class="icon-label">Discontinued (locked)</div>
        </div>
        <div class="icon-card">
          <div class="icon-demo" style="color:#94a3b8">&#9654;</div>
          <div class="icon-label">Chevron (expandable)</div>
        </div>
      </div>

      <h3>Chevron Rotation</h3>
      <p>Chevrons rotate 90&deg; on expand with <code>transition: transform 0.15s</code>.</p>

      <h3>Product Labels</h3>
      <p class="note">Textual icons with color coding. Responsive: full text on desktop, abbreviation on phone.</p>
      <div class="label-demos">
        <span class="cw-label launch">LAUNCH</span>
        <span class="cw-label disc">DISC.</span>
        <span class="cw-label old">OLD</span>
        <span class="cw-label gold">GOLD</span>
      </div>
      <table class="spec-table">
        <thead><tr><th>Label</th><th>Meaning</th><th>Background</th><th>Text</th></tr></thead>
        <tbody>
          <tr><td>LAUNCH</td><td>Recently launched product</td><td>#E8F5E9</td><td>#2E7D32</td></tr>
          <tr><td>DISC.</td><td>Discontinued by supplier</td><td>#ECEFF1</td><td>#616161</td></tr>
          <tr><td>OLD</td><td>Product is 5+ years old</td><td>#FFEBEE</td><td>#C62828</td></tr>
          <tr><td>GOLD</td><td>Gold material product</td><td>#FFF8E1</td><td>#BF360C</td></tr>
        </tbody>
      </table>

      <h3>Future Direction</h3>
      <div class="callout">
        If an icon library is ever adopted, prefer <strong>line icons, 1.5px stroke, rounded caps</strong>
        (Lucide or Phosphor style). No filled icons, no emoji-style.
      </div>
    </section>"""


def _sec_voice() -> str:
    return """
    <section id="voice">
      <h2>7. Voice &amp; Tone</h2>

      <p><strong>Overall voice:</strong> analyst-to-peer. Direct, specific, not dumbed down.
      We write for people who understand inventory and supply chain.</p>

      <h3>Tone by Context</h3>
      <div class="tone-grid">
        <div class="tone-card">
          <h4>Success</h4>
          <div class="tone-do">&ldquo;Changes saved&rdquo;</div>
          <div class="tone-do">&ldquo;3 products confirmed&rdquo;</div>
          <div class="tone-dont">&ldquo;Great job! Your changes have been saved successfully!&rdquo;</div>
        </div>
        <div class="tone-card">
          <h4>Error</h4>
          <div class="tone-do">&ldquo;Failed to save: network timeout&rdquo;</div>
          <div class="tone-do">&ldquo;Could not load data. Check your connection.&rdquo;</div>
          <div class="tone-dont">&ldquo;Oops! Something went wrong.&rdquo;</div>
        </div>
        <div class="tone-card">
          <h4>Empty State</h4>
          <div class="tone-do">&ldquo;No products match. Try broadening filters.&rdquo;</div>
          <div class="tone-dont">&ldquo;Nothing here yet! Start by adding some products.&rdquo;</div>
        </div>
        <div class="tone-card">
          <h4>Loading</h4>
          <div class="tone-do">Spinner only (no text for &lt;2s)</div>
          <div class="tone-do">&ldquo;Loading 1,247 products&hellip;&rdquo; (for &gt;2s)</div>
          <div class="tone-dont">&ldquo;Please wait while we load your data&hellip;&rdquo;</div>
        </div>
        <div class="tone-card">
          <h4>Destructive</h4>
          <div class="tone-do">&ldquo;Change 24 products from STOCK to NOT-STOCK?&rdquo;</div>
          <div class="tone-dont">&ldquo;Are you sure you want to proceed?&rdquo;</div>
        </div>
      </div>

      <h3>Case Conventions</h3>
      <table class="spec-table">
        <thead><tr><th>Context</th><th>Case</th><th>Example</th></tr></thead>
        <tbody>
          <tr><td>UI copy</td><td>Sentence case</td><td>Changes saved</td></tr>
          <tr><td>Section headers</td><td>Title Case</td><td>Global Assortment Review</td></tr>
          <tr><td>Badges / labels</td><td>UPPERCASE</td><td>STOCK, LAUNCH, DISC.</td></tr>
          <tr><td>Brand name</td><td>PascalCase</td><td>CatWing (never Catwing or CATWING)</td></tr>
        </tbody>
      </table>

      <h3>Number Formatting</h3>
      <table class="spec-table">
        <thead><tr><th>Type</th><th>Format</th><th>Example</th></tr></thead>
        <tbody>
          <tr><td>Currency (large)</td><td>&euro; prefix, no decimals, comma thousands</td><td>&euro;12,450</td></tr>
          <tr><td>Percentage</td><td>1 decimal</td><td>95.8%</td></tr>
          <tr><td>Quantity</td><td>Comma thousands</td><td>1,247</td></tr>
          <tr><td>Date (UI)</td><td>DD Mon YYYY</td><td>02 Mar 2026</td></tr>
          <tr><td>Date (filenames)</td><td>ISO 8601</td><td>2026-03-02</td></tr>
        </tbody>
      </table>

      <h3>Error Message Structure</h3>
      <p><code>[Failed to {action}]: {cause} ({recovery})</code></p>
      <p class="note">Example: &ldquo;Failed to save changes: network timeout (retry or check connection)&rdquo;</p>

      <h3>Notification Hierarchy</h3>
      <table class="spec-table">
        <thead><tr><th>Pattern</th><th>When</th><th>Duration</th><th>Example</th></tr></thead>
        <tbody>
          <tr><td><strong>Inline badge</strong></td><td>Status visible in context</td><td>Persistent</td><td>STOCK / NOT-STOCK badge on row</td></tr>
          <tr><td><strong>Toast (success)</strong></td><td>Action completed</td><td>Auto-dismiss 3s + undo 5s</td><td>&ldquo;3 products confirmed&rdquo;</td></tr>
          <tr><td><strong>Toast (error)</strong></td><td>Transient failure</td><td>Manual dismiss</td><td>&ldquo;Failed to save: timeout&rdquo;</td></tr>
          <tr><td><strong>Inline error</strong></td><td>Validation failure</td><td>Until fixed</td><td>Red border + message on input</td></tr>
          <tr><td><strong>Empty state</strong></td><td>No data to show</td><td>Until resolved</td><td>&ldquo;No products match. Broaden filters.&rdquo;</td></tr>
          <tr><td><strong>Modal</strong></td><td>Destructive / irreversible</td><td>User must act</td><td>&ldquo;Change 24 products to NOT-STOCK?&rdquo;</td></tr>
        </tbody>
      </table>
      <p class="spec">Rule: never use a modal for success. Never auto-dismiss errors. Always offer undo for bulk actions.</p>
    </section>"""


def _sec_components() -> str:
    return """
    <section id="components">
      <h2>8. Components</h2>

      <h3>Buttons</h3>
      <div class="component-row">
        <button class="cw-btn cw-btn-primary">Primary</button>
        <button class="cw-btn cw-btn-secondary">Secondary</button>
        <button class="cw-btn cw-btn-danger">Danger</button>
        <button class="cw-btn cw-btn-locked">Locked</button>
        <button class="cw-btn cw-btn-primary" disabled>Disabled</button>
      </div>
      <table class="spec-table">
        <thead><tr><th>Variant</th><th>When to Use</th></tr></thead>
        <tbody>
          <tr><td>Primary (gradient)</td><td>Main action: Save, Confirm, Submit</td></tr>
          <tr><td>Secondary (#e8edf4)</td><td>Alternative actions: Cancel, Close, Filter</td></tr>
          <tr><td>Danger (#ffebee)</td><td>Destructive: Delete, Unconfirm, Reset</td></tr>
          <tr><td>Locked (#999)</td><td>Supplier-discontinued products (not clickable)</td></tr>
        </tbody>
      </table>
      <p class="spec">Padding: 0.5rem 0.8rem &middot; Radius: 6px &middot; Font: 0.8rem/600 Poppins &middot; Transition: 0.2s</p>

      <h3>Button States</h3>
      <table class="spec-table">
        <thead><tr><th>State</th><th>Primary</th><th>Secondary</th><th>Danger</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>Default</strong></td>
            <td><button class="cw-btn cw-btn-primary btn-static">Save</button></td>
            <td><button class="cw-btn cw-btn-secondary btn-static">Cancel</button></td>
            <td><button class="cw-btn cw-btn-danger btn-static">Delete</button></td>
          </tr>
          <tr>
            <td><strong>Hover</strong></td>
            <td><button class="cw-btn cw-btn-primary btn-static" style="opacity:0.85;transform:translateY(-1px)">Save</button></td>
            <td><button class="cw-btn cw-btn-secondary btn-static" style="background:#dce3ed">Cancel</button></td>
            <td><button class="cw-btn cw-btn-danger btn-static" style="background:#ffcdd2">Delete</button></td>
          </tr>
          <tr>
            <td><strong>Focus</strong></td>
            <td><button class="cw-btn cw-btn-primary btn-static" style="box-shadow:0 0 0 3px rgba(32,176,165,0.3)">Save</button></td>
            <td><button class="cw-btn cw-btn-secondary btn-static" style="box-shadow:0 0 0 3px rgba(51,102,153,0.2)">Cancel</button></td>
            <td><button class="cw-btn cw-btn-danger btn-static" style="box-shadow:0 0 0 3px rgba(244,67,54,0.2)">Delete</button></td>
          </tr>
          <tr>
            <td><strong>Disabled</strong></td>
            <td><button class="cw-btn cw-btn-primary btn-static" disabled>Save</button></td>
            <td><button class="cw-btn cw-btn-secondary btn-static" disabled>Cancel</button></td>
            <td><button class="cw-btn cw-btn-danger btn-static" disabled>Delete</button></td>
          </tr>
        </tbody>
      </table>

      <h3>Input States</h3>
      <div class="input-states-demo">
        <div class="input-state-card">
          <div class="input-state-label">Default</div>
          <div class="cw-input-demo">Search products&hellip;</div>
        </div>
        <div class="input-state-card">
          <div class="input-state-label">Focused</div>
          <div class="cw-input-demo focused">T-Sport</div>
        </div>
        <div class="input-state-card">
          <div class="input-state-label">Error</div>
          <div class="cw-input-demo error">-5</div>
          <div class="input-error-msg">Quantity must be positive</div>
        </div>
      </div>

      <h3>Status Badges</h3>
      <div class="component-row">
        <span class="cw-badge stock cw-badge-interactive">STOCK</span>
        <span class="cw-badge not-stock cw-badge-interactive">NOT-STOCK</span>
        <span class="cw-badge outlined-stock">STOCK</span>
        <span class="cw-badge outlined-notstock">NOT-STOCK</span>
        <span class="cw-badge stock locked">STOCK (locked)</span>
      </div>
      <p class="spec">Solid = client status (click to toggle) &middot; Outlined = CW recommendation (read-only) &middot; Locked = opacity 0.5, cursor not-allowed</p>

      <h3>Product Labels</h3>
      <div class="component-row">
        <span class="cw-label launch">LAUNCH</span>
        <span class="cw-label disc">DISC.</span>
        <span class="cw-label old">OLD</span>
        <span class="cw-label gold">GOLD</span>
      </div>
      <p class="spec">Padding: 1px 6px &middot; Radius: 3px &middot; Font: 0.65rem/700 &middot; Responsive: full text &rarr; abbreviation on phone</p>

      <h3>Cards</h3>
      <div class="component-row">
        <div class="cw-card">
          <div class="cw-card-value">1,247</div>
          <div class="cw-card-label">TOTAL PRODUCTS</div>
        </div>
        <div class="cw-card stock">
          <div class="cw-card-value">892</div>
          <div class="cw-card-label">STOCK</div>
        </div>
        <div class="cw-card notstock">
          <div class="cw-card-value">355</div>
          <div class="cw-card-label">NOT-STOCK</div>
        </div>
      </div>

      <h3>Form Inputs</h3>
      <div class="component-row inputs">
        <input type="text" class="cw-input" placeholder="Default input" readonly>
        <input type="text" class="cw-input focus" value="Focused (blue border)" readonly>
        <input type="text" class="cw-input error" value="Error (red border)" readonly>
      </div>
      <p class="spec">Border: 1px solid #cdd5e0 &middot; Radius: 6px &middot; Focus: CW Blue border + shadow &middot; Error: red border + shadow</p>

      <h3>Table</h3>
      <div class="cw-table-wrap">
        <table class="cw-table">
          <thead><tr>
            <th>Product</th><th>Status</th><th>Revenue</th><th>Zone</th>
          </tr></thead>
          <tbody>
            <tr><td>Tissot PRX 35mm</td><td><span class="cw-badge stock">STOCK</span></td><td class="num">&euro;12,450</td><td><span class="cw-zone green"></span>A</td></tr>
            <tr class="confirmed-row"><td>Certina DS Action</td><td><span class="cw-badge stock">STOCK</span></td><td class="num">&euro;8,320</td><td><span class="cw-zone yellow"></span>B</td></tr>
            <tr class="drift-row"><td>Swatch Gent</td><td><span class="cw-badge not-stock">NOT-STOCK</span></td><td class="num">&euro;1,890</td><td><span class="cw-zone red"></span>D</td></tr>
          </tbody>
        </table>
      </div>
      <p class="spec">Header: CW Blue bg, white text, sticky &middot; Confirmed: #E8F5E9 + 4px green border &middot; Drift: #FFF3E0 + 4px orange border</p>

      <h3>Toast Notifications</h3>
      <div class="component-row">
        <div class="cw-toast success">Changes saved <button class="cw-toast-action">Undo</button></div>
        <div class="cw-toast error">Failed to save changes</div>
        <div class="cw-toast info">Loading data&hellip;</div>
      </div>
      <p class="spec">Bottom-right fixed &middot; z-index: 1000 &middot; Slide-up 0.3s ease-out &middot; Undo button: 5s window &middot; Auto-dismiss</p>

      <h3>Modal</h3>
      <div class="cw-modal-demo">
        <div class="cw-modal-card">
          <h3>Confirm Status Change</h3>
          <p>Change 24 products from STOCK to NOT-STOCK?</p>
          <div class="cw-modal-actions">
            <button class="cw-btn cw-btn-secondary">Cancel</button>
            <button class="cw-btn cw-btn-primary">Confirm</button>
          </div>
        </div>
      </div>
      <p class="spec">Overlay: rgba(0,0,0,0.4) &middot; Card: white, 10px radius, max-width 420px &middot; z-index: 2000</p>

      <h3>Progress Bar</h3>
      <div class="progress-demo">
        <div class="progress-track">
          <div class="progress-fill" style="width:72%"></div>
          <div class="progress-label">72% reviewed</div>
        </div>
      </div>

      <h3>Phase-out Bar</h3>
      <div class="phaseout-demo">
        <span class="phaseout-label">Phase-out:</span>
        <div class="phaseout-track">
          <div class="phaseout-fill" style="width:73%"></div>
        </div>
        <span class="phaseout-value">73/100</span>
      </div>
      <p class="spec">Gradient: orange &rarr; red (linear-gradient(90deg, #FF9800, #D32F2F)) &middot; 120px wide, 6px tall</p>

      <h3>Coverage Bar (Segmented Availability)</h3>
      <div class="coverage-bar-demo">
        <table class="coverage-bar-table">
          <thead>
            <tr>
              <th>Product</th>
              <th>Stock Availability</th>
              <th>Days&rsquo; Supply</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>T-Sport XL</td>
              <td>
                <div class="coverage-segments">
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                </div>
              </td>
              <td class="coverage-days high">180</td>
            </tr>
            <tr>
              <td>PRX Powermatic</td>
              <td>
                <div class="coverage-segments">
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg warn"></div><div class="coverage-seg warn"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                </div>
              </td>
              <td class="coverage-days mid">9</td>
            </tr>
            <tr>
              <td>Gentleman Quartz</td>
              <td>
                <div class="coverage-segments">
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg ok"></div><div class="coverage-seg ok"></div>
                  <div class="coverage-seg warn"></div><div class="coverage-seg warn"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                </div>
              </td>
              <td class="coverage-days low">3</td>
            </tr>
            <tr>
              <td>Seastar 1000</td>
              <td>
                <div class="coverage-segments">
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                  <div class="coverage-seg bad"></div><div class="coverage-seg bad"></div>
                </div>
              </td>
              <td class="coverage-days low">0</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="spec">Each segment = 1 week of supply &middot; Green #4CAF50 (covered) &middot; Orange #FF9800 (at risk) &middot; Red #D32F2F (shortage) &middot; 18px tall, 1px gap</p>
    </section>"""


def _sec_interactions() -> str:
    return """
    <section id="interactions">
      <h2>9. Interaction Patterns</h2>

      <h3>Keyboard Navigation</h3>
      <div class="key-grid">
        <div class="key-card"><span class="key-cap">J</span><span class="key-desc">Next product</span></div>
        <div class="key-card"><span class="key-cap">K</span><span class="key-desc">Previous product</span></div>
        <div class="key-card"><span class="key-cap">Enter</span><span class="key-desc">Toggle confirm</span></div>
        <div class="key-card"><span class="key-cap">S</span><span class="key-desc">Toggle status</span></div>
        <div class="key-card"><span class="key-cap">I</span><span class="key-desc">Toggle thumbnails</span></div>
        <div class="key-card"><span class="key-cap">Esc</span><span class="key-desc">Deselect / close</span></div>
      </div>
      <p class="note">Keyboard shortcuts disabled when typing in input/textarea/select fields.</p>

      <h3>Click Patterns</h3>
      <table class="interaction-table">
        <thead><tr><th>Action</th><th>Gesture</th><th>Timing</th></tr></thead>
        <tbody>
          <tr><td>Select product</td><td>Single click on row</td><td>Immediate</td></tr>
          <tr><td>Toggle confirm</td><td>Double click on row</td><td>200ms disambiguation</td></tr>
          <tr><td>Toggle status badge</td><td>Click badge</td><td>300ms throttle (cooldown)</td></tr>
          <tr><td>Expand subcollection</td><td>Click sub-row</td><td>Immediate</td></tr>
        </tbody>
      </table>

      <h3>Optimistic Updates</h3>
      <div class="callout">
        <strong>Pattern:</strong> Immediate UI update &rarr; server call &rarr; reconcile on response &rarr;
        revert on failure + error toast. Undo toast visible for <strong>5 seconds</strong>.
      </div>

      <h3>Hover Previews</h3>
      <ul>
        <li><strong>Delay:</strong> 300ms before showing</li>
        <li><strong>Size:</strong> 200&times;200px product image</li>
        <li><strong>Positioning:</strong> Viewport-aware (avoids going off-screen)</li>
        <li><strong>Touch:</strong> Disabled on touch devices via <code>@media (hover: none)</code></li>
      </ul>

      <h3>Debounced Saves</h3>
      <ul>
        <li><strong>Notes textarea:</strong> 500ms debounce on input + save on blur</li>
        <li><strong>Filter changes:</strong> Immediate (no debounce)</li>
      </ul>

      <h3>Sidebar Behavior</h3>
      <table class="interaction-table">
        <thead><tr><th>Breakpoint</th><th>Behavior</th></tr></thead>
        <tbody>
          <tr><td>Desktop (&gt;768px)</td><td>Always visible, 260px fixed</td></tr>
          <tr><td>Tablet (&le;768px)</td><td>Hamburger button + overlay slide-in</td></tr>
          <tr><td>Phone (&le;480px)</td><td>Full-width slide-in</td></tr>
        </tbody>
      </table>
    </section>"""


def _sec_states() -> str:
    return """
    <section id="states">
      <h2>10. State Patterns</h2>

      <div class="state-grid">
        <div class="state-card">
          <div class="state-card-header">Loading</div>
          <div class="state-card-body">
            <div class="spinner-demo"></div>
            <p class="spec text-center">24px &middot; 3px border &middot; CW Blue top &middot; 0.8s linear infinite</p>
          </div>
        </div>

        <div class="state-card">
          <div class="state-card-header">Empty</div>
          <div class="state-card-body">
            <div class="empty-state-demo">
              No products match.<br>Try broadening filters.
            </div>
          </div>
        </div>

        <div class="state-card">
          <div class="state-card-header">Error (inline)</div>
          <div class="state-card-body">
            <div class="error-state-demo">Failed to load: network timeout</div>
          </div>
        </div>

        <div class="state-card">
          <div class="state-card-header">Success (row)</div>
          <div class="state-card-body">
            <div class="state-row-demo state-row-success">
              Certina DS Action &mdash; <span class="cw-badge stock badge-mini">STOCK</span>
            </div>
          </div>
        </div>

        <div class="state-card">
          <div class="state-card-header">Drift / Warning (row)</div>
          <div class="state-card-body">
            <div class="state-row-demo state-row-drift">
              Swatch Gent &mdash; <span class="drift-icon">&#9888; Re-review needed</span>
            </div>
          </div>
        </div>

        <div class="state-card">
          <div class="state-card-header">Disabled</div>
          <div class="state-card-body text-center">
            <button class="cw-btn cw-btn-primary" disabled>Disabled</button>
            <p class="spec">opacity: 0.5 &middot; cursor: not-allowed</p>
          </div>
        </div>

        <div class="state-card">
          <div class="state-card-header">Image Placeholder</div>
          <div class="state-card-body">
            <div class="img-placeholder-demo">No image</div>
            <p class="spec text-center">180&times;180px &middot; grey bg &middot; rounded</p>
          </div>
        </div>
      </div>

      <h3>State Transition Rules</h3>
      <div class="callout">
        <strong>Never flash loading for &lt;200ms responses.</strong> If the server responds within 200ms,
        skip the loading state entirely and go straight to the result.
      </div>
      <ul>
        <li><strong>Error tiers:</strong> Red toast (transient, auto-dismiss) &rarr; Inline red border (validation) &rarr; Modal (critical/destructive)</li>
        <li><strong>Success:</strong> Green toast (auto-dismiss) + row highlight (persistent)</li>
        <li><strong>Drift:</strong> Orange row highlight + re-review badge (persistent until confirmed)</li>
      </ul>
    </section>"""


def _sec_layout() -> str:
    return """
    <section id="layout">
      <h2>11. Layout &amp; Spacing</h2>

      <h3>Spacing Scale</h3>
      <div class="spacing-demo">
        <div class="sp" style="width:4px"><span>4px</span></div>
        <div class="sp" style="width:8px"><span>8px</span></div>
        <div class="sp" style="width:12px"><span>12px</span></div>
        <div class="sp" style="width:16px"><span>16px</span></div>
        <div class="sp" style="width:20px"><span>20px</span></div>
        <div class="sp" style="width:24px"><span>24px</span></div>
      </div>
      <p class="spec">Base unit: 4px (0.25rem at 16px root). Application uses rem for all spacing.</p>
      <table class="spec-table">
        <thead><tr><th>Token</th><th>px</th><th>rem</th><th>Usage</th></tr></thead>
        <tbody>
          <tr><td>xs</td><td>4px</td><td>0.25rem</td><td>Badge padding, tight gaps</td></tr>
          <tr><td>sm</td><td>8px</td><td>0.5rem</td><td>Button padding, table cell spacing</td></tr>
          <tr><td>md</td><td>12px</td><td>0.75rem</td><td>Card inner padding</td></tr>
          <tr><td>base</td><td>16px</td><td>1rem</td><td>Section gaps, standard padding</td></tr>
          <tr><td>lg</td><td>20px</td><td>1.25rem</td><td>Component spacing</td></tr>
          <tr><td>xl</td><td>24px</td><td>1.5rem</td><td>Section spacing, large gaps</td></tr>
        </tbody>
      </table>

      <h3>Border Radius Scale</h3>
      <div class="radius-demo">
        <div class="rad" style="border-radius:4px"><span>4px</span><em>Badges</em></div>
        <div class="rad" style="border-radius:6px"><span>6px</span><em>Inputs, buttons</em></div>
        <div class="rad" style="border-radius:8px"><span>8px</span><em>Cards (default)</em></div>
        <div class="rad" style="border-radius:10px"><span>10px</span><em>Headers, modals</em></div>
        <div class="rad" style="border-radius:12px"><span>12px</span><em>Elevated cards</em></div>
      </div>

      <h3>Shadow Scale</h3>
      <div class="shadow-demo">
        <div class="sh" style="box-shadow:0 2px 8px rgba(0,0,0,0.08)"><strong>Standard</strong><code>0 2px 8px rgba(0,0,0,0.08)</code></div>
        <div class="sh" style="box-shadow:0 4px 16px rgba(0,0,0,0.15)"><strong>Elevated</strong><code>0 4px 16px rgba(0,0,0,0.15)</code></div>
        <div class="sh" style="box-shadow:0 8px 32px rgba(0,0,0,0.15)"><strong>Modal</strong><code>0 8px 32px rgba(0,0,0,0.15)</code></div>
      </div>

      <h3>Z-Index Scale</h3>
      <table class="zindex-table">
        <thead><tr><th>Layer</th><th>Value</th><th>Usage</th></tr></thead>
        <tbody>
          <tr><td>Base content</td><td>auto</td><td>Default stacking</td></tr>
          <tr><td>Sticky header</td><td>10</td><td>Table thead</td></tr>
          <tr><td>Sidebar overlay</td><td>99</td><td>Background dimmer</td></tr>
          <tr><td>Sidebar</td><td>100</td><td>Mobile slide-in sidebar</td></tr>
          <tr><td>Hamburger button</td><td>110</td><td>Always above sidebar</td></tr>
          <tr><td>Hover preview</td><td>500</td><td>Image preview tooltip</td></tr>
          <tr><td>Toast</td><td>1000</td><td>Notification toasts</td></tr>
          <tr><td>Modal</td><td>2000</td><td>Confirm dialogs</td></tr>
        </tbody>
      </table>

      <h3>App Layout</h3>
      <div class="layout-diagram">
        <div class="ld-sidebar">Sidebar<br>260px fixed</div>
        <div class="ld-main">
          <div class="ld-header">Header (gradient, 10px radius)</div>
          <div class="ld-content">Content area (flex column, 1rem gap)</div>
        </div>
      </div>

      <h3>Responsive Breakpoints</h3>
      <table class="spec-table">
        <thead><tr><th>Breakpoint</th><th>Width</th><th>Changes</th></tr></thead>
        <tbody>
          <tr><td>Desktop</td><td>&gt;768px</td><td>Full sidebar + content, all columns visible</td></tr>
          <tr><td>Tablet</td><td>&le;768px</td><td>Hamburger menu, overlay sidebar, hide Age column</td></tr>
          <tr><td>Phone</td><td>&le;480px</td><td>Full-width sidebar, hide Revenue/Qty/Zone, 2-line product cell</td></tr>
        </tbody>
      </table>

      <h3>Column Progressive Disclosure</h3>
      <table class="spec-table">
        <thead><tr><th>Column</th><th>Desktop</th><th>Tablet</th><th>Phone</th></tr></thead>
        <tbody>
          <tr><td>Product</td><td>Visible</td><td>Visible</td><td>Visible (+ meta row)</td></tr>
          <tr><td>Revenue</td><td>Visible</td><td>Visible</td><td>Hidden</td></tr>
          <tr><td>Qty</td><td>Visible</td><td>Visible</td><td>Hidden</td></tr>
          <tr><td>Age</td><td>Visible</td><td>Hidden</td><td>Hidden</td></tr>
          <tr><td>Zone</td><td>Visible</td><td>Visible</td><td>Hidden</td></tr>
          <tr><td>Status</td><td>Visible</td><td>Visible</td><td>Visible</td></tr>
        </tbody>
      </table>

      <div class="density-callout">
        &ldquo;Show more, annotate less. Tables over cards. Numbers over charts. Context on demand.&rdquo;
      </div>

      <h3>Responsive Testing Checklist</h3>
      <table class="spec-table">
        <thead><tr><th>Check</th><th>Desktop &gt;768px</th><th>Tablet &le;768px</th><th>Phone &le;480px</th></tr></thead>
        <tbody>
          <tr><td>Sidebar</td><td>Fixed 260px, always visible</td><td>Hamburger + overlay slide</td><td>Full-width overlay</td></tr>
          <tr><td>Table scroll</td><td>No overflow</td><td>Horizontal scroll if needed</td><td>Horizontal scroll, key cols only</td></tr>
          <tr><td>Hover previews</td><td>300ms delay, 200&times;200px</td><td>Disabled</td><td>Disabled</td></tr>
          <tr><td>Detail panel</td><td>Right panel 400px</td><td>Full-width modal</td><td>Full-width modal</td></tr>
          <tr><td>Keyboard nav</td><td>J/K/Enter/S/Escape</td><td>Touch + swipe</td><td>Touch + swipe</td></tr>
          <tr><td>Font size</td><td>14px base</td><td>14px base</td><td>14px base (no reduction)</td></tr>
        </tbody>
      </table>
    </section>"""


def _sec_motion() -> str:
    return """
    <section id="motion">
      <h2>12. Motion &amp; Animation</h2>

      <h3>Transition Durations</h3>
      <table class="spec-table">
        <thead><tr><th>Duration</th><th>Use Case</th><th>Example</th></tr></thead>
        <tbody>
          <tr><td><strong>0.15s</strong></td><td>Micro-interactions</td><td>Chevron rotation, button state, badge hover</td></tr>
          <tr><td><strong>0.25s</strong></td><td>Navigation</td><td>Sidebar slide in/out, overlay fade</td></tr>
          <tr><td><strong>0.3s</strong></td><td>Feedback</td><td>Toast slide-up, progress bar fill</td></tr>
        </tbody>
      </table>

      <h3>Easing Functions</h3>
      <table class="spec-table">
        <thead><tr><th>Function</th><th>Use</th></tr></thead>
        <tbody>
          <tr><td><code>ease-out</code></td><td>Entrances (toast in, sidebar open)</td></tr>
          <tr><td><code>ease</code></td><td>State changes (hover, focus, color transitions)</td></tr>
          <tr><td><code>linear</code></td><td>Continuous motion (spinner rotation)</td></tr>
        </tbody>
      </table>

      <h3>Keyframes</h3>
      <pre><code>@keyframes toast-in {
  from { transform: translateY(20px); opacity: 0; }
  to   { transform: translateY(0); opacity: 1; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Hamburger morph: 3 bars → ✕ */
.open .hamburger::before  { transform: translateY(6px) rotate(45deg); }
.open .hamburger span     { opacity: 0; }
.open .hamburger::after   { transform: translateY(-6px) rotate(-45deg); }</code></pre>

      <h3>Live Demos</h3>
      <div class="component-row">
        <button class="cw-btn cw-btn-primary motion-demo">Hover me (0.2s ease)</button>
        <span class="chevron-arrow">&#9654; Click to rotate (0.15s)</span>
      </div>

      <div class="toast-trigger-area">
        <button class="cw-btn cw-btn-primary" id="toast-trigger">Trigger toast demo</button>
      </div>

      <div class="callout">
        <strong>Rule:</strong> Every animation serves a purpose. No decorative motion, no bouncing, no parallax.
      </div>
    </section>"""


def _sec_darkmode() -> str:
    return """
    <section id="darkmode">
      <h2>13. Dark Mode</h2>

      <p class="note">Toggle the theme using the button in the navigation sidebar to see this guide adapt in real-time.</p>

      <h3>Dark Palette Mapping</h3>
      <table class="spec-table">
        <thead><tr><th>Element</th><th>Light</th><th>Dark</th></tr></thead>
        <tbody>
          <tr><td>Page background</td><td><span class="chip" style="background:#f5f7fa"></span> #f5f7fa</td><td><span class="chip" style="background:#0f1923"></span> #0f1923</td></tr>
          <tr><td>Surface (cards)</td><td><span class="chip" style="background:#ffffff;border:1px solid #ddd"></span> #ffffff</td><td><span class="chip" style="background:#1a2332"></span> #1a2332</td></tr>
          <tr><td>Borders</td><td><span class="chip" style="background:#dce3ed"></span> #dce3ed</td><td><span class="chip" style="background:#2a3a4a"></span> #2a3a4a</td></tr>
          <tr><td>Primary text</td><td><span class="chip" style="background:#1c1c1c"></span> #1c1c1c</td><td><span class="chip" style="background:#e2e8f0"></span> #e2e8f0</td></tr>
          <tr><td>Muted text</td><td><span class="chip" style="background:#666"></span> #666</td><td><span class="chip" style="background:#94a3b8"></span> #94a3b8</td></tr>
        </tbody>
      </table>
      <p class="note">Status colors (green #4CAF50, red #D32F2F, orange #FF9800) remain unchanged on dark backgrounds.</p>

      <h3>Implementation</h3>
      <pre><code>:root {
  --guide-bg: #f5f7fa;
  --guide-surface: #ffffff;
  --guide-text: #1c1c1c;
  --guide-border: #dce3ed;
}

[data-theme="dark"] {
  --guide-bg: #0f1923;
  --guide-surface: #1a2332;
  --guide-text: #e2e8f0;
  --guide-border: #2a3a4a;
}</code></pre>
      <p class="note">Toggle via <code>data-theme="dark"</code> on <code>&lt;html&gt;</code>. Persisted to localStorage. Respects <code>prefers-color-scheme</code> as default.</p>

      <h3>Side-by-Side Comparison</h3>
      <div class="dark-compare">
        <div class="compare-panel light-panel">
          <div class="compare-header">Light Mode</div>
          <div class="compare-card">
            <strong style="color:#1c1c1c">Product Title</strong>
            <p style="color:#555">Subtitle text on white surface</p>
            <span class="cw-badge stock">STOCK</span>
          </div>
        </div>
        <div class="compare-panel dark-panel">
          <div class="compare-header">Dark Mode</div>
          <div class="compare-card" style="background:#1a2332">
            <strong style="color:#e2e8f0">Product Title</strong>
            <p style="color:#94a3b8">Subtitle text on dark surface</p>
            <span class="cw-badge stock">STOCK</span>
          </div>
        </div>
      </div>

      <h3>Logo on Dark</h3>
      <p>The wing icon works on both light and dark backgrounds.
      Wordmark: white &ldquo;Cat&rdquo; + CW Presentation Teal &ldquo;Wing&rdquo; on dark.</p>
    </section>"""


def _sec_dataviz() -> str:
    palette_order = [
        ("#336699", "CW Blue"),
        ("#20b0a5", "CW Teal"),
        ("#42A5F5", "Blue"),
        ("#27AE60", "Green"),
        ("#F39C12", "Amber"),
        ("#C0392B", "Red"),
        ("#8E44AD", "Purple"),
        ("#17A589", "Teal"),
    ]
    chips = ""
    for i, (color, name) in enumerate(palette_order):
        chips += f'<div class="dv-chip" style="background:{color}"><span>{i + 1}</span>{name}</div>'

    return f"""
    <section id="dataviz">
      <h2>14. Data Visualization</h2>

      <h3>Chart Color Priority</h3>
      <p class="note">Use colors in this order. First 2 are brand colors; remainder for multi-series charts.</p>
      <div class="dv-palette">{chips}</div>

      <h3>Axis &amp; Grid Styling</h3>
      <ul>
        <li>Grid lines: <code>#e0e0e0</code> at 0.5px, no chart borders</li>
        <li>Axis labels: <code>#666666</code>, Poppins 0.8rem (or Calibri for PPTX)</li>
        <li>Title: Poppins 600, CW Dark (#1c1c1c)</li>
      </ul>

      <h3>Sequential Palette (Heat Maps)</h3>
      <div class="heatmap-demo">
        <div style="background:#f7fcf5">Low</div>
        <div style="background:#c7e9c0">&nbsp;</div>
        <div style="background:#74c476">&nbsp;</div>
        <div style="background:#238b45">&nbsp;</div>
        <div style="background:#00441b;color:#fff">High</div>
      </div>
      <p class="spec">Recommended: Viridis or Greens sequential. Never use rainbow colormaps.</p>

      <h3>Inventory Timeline</h3>
      <div class="chart-demo">
        <div class="chart-title">Inventory Level &amp; Restock Events</div>
        <div class="chart-legend">
          <span class="chart-legend-item"><span class="chart-legend-swatch" style="background:#336699"></span> Inventory</span>
          <span class="chart-legend-item"><span class="chart-legend-swatch triangle"></span> Restock</span>
          <span class="chart-legend-item"><span class="chart-legend-swatch diamond"></span> PO</span>
          <span class="chart-legend-item"><span class="chart-legend-swatch" style="background:#F39C12"></span> Stockout Qty</span>
        </div>
        <div class="line-chart-wrap">
          <div class="line-chart-ylabels">
            <span>12</span><span>9</span><span>6</span><span>3</span><span>0</span>
          </div>
          <svg class="line-chart-svg" viewBox="0 0 800 200" preserveAspectRatio="xMidYMid meet">
            <defs>
              <!-- projection zone hatching -->
              <pattern id="proj-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="6" stroke="#336699" stroke-width="0.5" stroke-opacity="0.08"/>
              </pattern>
            </defs>
            <!-- grid lines -->
            <g class="svg-grid" stroke="#e0e0e0" stroke-width="0.5">
              <line x1="0" y1="10" x2="800" y2="10"/>
              <line x1="0" y1="57" x2="800" y2="57"/>
              <line x1="0" y1="104" x2="800" y2="104"/>
              <line x1="0" y1="151" x2="800" y2="151"/>
              <line x1="0" y1="190" x2="800" y2="190"/>
            </g>

            <!-- "Now" divider & projection zone -->
            <rect x="640" y="0" width="160" height="200" fill="url(#proj-hatch)"/>
            <line x1="640" y1="0" x2="640" y2="200" stroke="#666" stroke-width="1.2" stroke-dasharray="6,4"/>
            <text class="svg-now-text" x="644" y="12" font-size="9" font-weight="600" fill="#555" font-family="Poppins, sans-serif">Now</text>
            <text class="svg-proj-text" x="700" y="12" font-size="8" fill="#777" font-family="Poppins, sans-serif" font-style="italic">Projection</text>

            <!-- area fill — historical (clipped at Now) -->
            <path d="M0,46 L40,57 L80,57 L120,57 L170,75 L210,75
                     L260,95 L310,116 L360,133 L420,151 L470,133
                     L520,104 L560,95 L600,104 L640,110
                     L640,190 L0,190 Z"
                  fill="#336699" fill-opacity="0.15"/>

            <!-- area fill — projection (after Now, lighter) -->
            <path d="M640,110 L680,110 L720,116 L760,116 L800,116
                     L800,190 L640,190 Z"
                  fill="#336699" fill-opacity="0.06"/>

            <!-- inventory line — historical (solid) -->
            <polyline points="0,46 40,57 80,57 120,57 170,75 210,75
                              260,95 310,116 360,133 420,151 470,133
                              520,104 560,95 600,104 640,110"
                      fill="none" stroke="#336699" stroke-width="2" stroke-linejoin="round"/>

            <!-- inventory line — projection (dashed) -->
            <polyline points="640,110 680,110 720,116 760,116 800,116"
                      fill="none" stroke="#336699" stroke-width="2"
                      stroke-linejoin="round" stroke-dasharray="6,4"/>

            <!-- PO diamonds (at top, like reference) -->
            <g class="svg-po-marker" fill="#7B1FA2">
              <polygon points="80,18 86,24 80,30 74,24" />  <!-- PO:5 -->
              <polygon points="170,18 176,24 170,30 164,24"/> <!-- PO:3 -->
              <polygon points="260,18 266,24 260,30 254,24"/> <!-- PO:1 -->
              <polygon points="420,18 426,24 420,30 414,24"/> <!-- PO:5 -->
              <polygon points="520,18 526,24 520,30 514,24"/> <!-- PO:1 -->
              <polygon points="680,18 686,24 680,30 674,24"/> <!-- PO:1 projected -->
              <polygon points="760,18 766,24 760,30 754,24"/> <!-- PO:2 projected -->
            </g>
            <g class="svg-po-text" fill="#7B1FA2" font-size="7.5" font-weight="600" text-anchor="middle" font-family="Poppins, sans-serif">
              <text x="80" y="14">PO:5</text><text x="170" y="14">PO:3</text>
              <text x="260" y="14">PO:1</text><text x="420" y="14">PO:5</text>
              <text x="520" y="14">PO:1</text>
              <text x="680" y="14" opacity="0.6">PO:1</text>
              <text x="760" y="14" opacity="0.6">PO:2</text>
            </g>

            <!-- restock triangles (green, on the inventory line) -->
            <g class="svg-restock-marker" fill="#2E7D32">
              <polygon points="40,57 46,46 34,46"/>   <!-- +3 -->
              <polygon points="170,75 176,64 164,64"/> <!-- +5 -->
              <polygon points="470,133 476,122 464,122"/> <!-- +5 -->
              <polygon points="520,104 526,93 514,93"/>   <!-- +3 -->
              <polygon points="680,110 686,99 674,99"/>   <!-- +1 proj -->
            </g>
            <g class="svg-restock-text" fill="#2E7D32" font-size="7.5" font-weight="600" text-anchor="middle" font-family="Poppins, sans-serif">
              <text x="40" y="42">+3</text><text x="170" y="60">+5</text>
              <text x="470" y="118">+5</text><text x="520" y="89">+3</text>
              <text x="680" y="95" opacity="0.6">+1</text>
            </g>

            <!-- dots on inventory line -->
            <g fill="#336699">
              <circle cx="0" cy="46" r="3"/><circle cx="80" cy="57" r="3"/>
              <circle cx="170" cy="75" r="3"/><circle cx="260" cy="95" r="3"/>
              <circle cx="360" cy="133" r="3"/><circle cx="470" cy="133" r="3"/>
              <circle cx="560" cy="95" r="3"/><circle cx="640" cy="110" r="3"/>
            </g>
            <!-- projection dots (hollow) -->
            <g class="svg-inv-dot-proj" fill="none" stroke="#336699" stroke-width="1.5">
              <circle cx="680" cy="110" r="3"/><circle cx="760" cy="116" r="3"/>
              <circle cx="800" cy="116" r="3"/>
            </g>

            <!-- stockout line — historical -->
            <polyline points="0,186 80,183 170,186 260,180 360,183
                              420,180 470,175 520,183 600,183 640,186"
                      fill="none" stroke="#F39C12" stroke-width="1.5"
                      stroke-linejoin="round"/>
            <!-- stockout dots -->
            <g fill="none" stroke="#F39C12" stroke-width="1.2">
              <circle cx="0" cy="186" r="3"/><circle cx="80" cy="183" r="3"/>
              <circle cx="260" cy="180" r="3"/><circle cx="420" cy="180" r="3"/>
              <circle cx="520" cy="183" r="3"/><circle cx="640" cy="186" r="3"/>
            </g>

            <!-- axes -->
            <line class="svg-axis" x1="0" y1="190" x2="800" y2="190" stroke="#666" stroke-width="1"/>
            <line class="svg-axis" x1="0" y1="10" x2="0" y2="190" stroke="#666" stroke-width="1"/>
          </svg>
        </div>
        <div class="line-chart-xlabels">
          <span>Jul 2024</span><span>Sep</span><span>Nov</span><span>Jan 2025</span>
          <span>Mar</span><span>May</span><span>Jul</span><span>Sep</span>
          <span>Nov</span><span>Jan 2026</span><span>Mar</span>
        </div>
      </div>
      <p class="spec">Area fill: 15% opacity (6% in projection zone) &middot; Line: 2px solid (dashed after &ldquo;Now&rdquo;) &middot; Restock: green triangles with +N label &middot; PO: purple diamonds with PO:N label (faded in projection) &middot; Stockout: orange line with hollow dots &middot; Projection zone: diagonal hatching</p>

      <h3>Demand vs Sales Bar Chart</h3>
      <div class="chart-demo">
        <div class="chart-title">Demand vs Sales ($ = discounted sale)</div>
        <div class="chart-legend">
          <span class="chart-legend-item"><span class="chart-legend-swatch bar" style="background:#F39C12;opacity:0.7"></span> Demand</span>
          <span class="chart-legend-item"><span class="chart-legend-swatch bar" style="background:#4CAF50"></span> Sales (Total)</span>
        </div>
        <div class="bar-chart-wrap">
          <div class="bar-chart-ylabels">
            <span>5</span><span>4</span><span>3</span><span>2</span><span>1</span><span>0</span>
          </div>
          <svg class="line-chart-svg" viewBox="0 0 800 180" preserveAspectRatio="xMidYMid meet">
            <!-- grid -->
            <g class="svg-grid" stroke="#e0e0e0" stroke-width="0.5">
              <line x1="0" y1="10" x2="800" y2="10"/>
              <line x1="0" y1="44" x2="800" y2="44"/>
              <line x1="0" y1="78" x2="800" y2="78"/>
              <line x1="0" y1="112" x2="800" y2="112"/>
              <line x1="0" y1="146" x2="800" y2="146"/>
              <line x1="0" y1="170" x2="800" y2="170"/>
            </g>
            <!-- axes -->
            <line class="svg-axis" x1="0" y1="170" x2="800" y2="170" stroke="#666" stroke-width="1"/>
            <line class="svg-axis" x1="0" y1="10" x2="0" y2="170" stroke="#666" stroke-width="1"/>
            <!-- y-axis label -->
            <text class="svg-axis-text" x="-85" y="4" transform="rotate(-90)" font-size="9" fill="#666" font-family="Poppins, sans-serif">Quantity</text>
            <!-- bar groups (demand behind, sales in front) — 12 months -->
            <!-- Apr -->
            <rect x="18" y="116" width="22" height="54" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="40" y="126" width="22" height="44" rx="2" fill="#4CAF50"/>
            <!-- May -->
            <rect x="84" y="90" width="22" height="80" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="106" y="106" width="22" height="64" rx="2" fill="#4CAF50"/>
            <!-- Jun -->
            <rect x="150" y="56" width="22" height="114" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="172" y="72" width="22" height="98" rx="2" fill="#4CAF50"/>
            <!-- Jul -->
            <rect x="216" y="96" width="22" height="74" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="238" y="116" width="22" height="54" rx="2" fill="#4CAF50"/>
            <!-- Aug -->
            <rect x="282" y="66" width="22" height="104" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="304" y="76" width="22" height="94" rx="2" fill="#4CAF50"/>
            <!-- Sep -->
            <rect x="348" y="28" width="22" height="142" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="370" y="42" width="22" height="128" rx="2" fill="#4CAF50"/>
            <!-- Oct -->
            <rect x="414" y="82" width="22" height="88" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="436" y="112" width="22" height="58" rx="2" fill="#4CAF50"/>
            <!-- Nov -->
            <rect x="480" y="96" width="22" height="74" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="502" y="138" width="22" height="32" rx="2" fill="#4CAF50"/>
            <!-- Dec -->
            <rect x="546" y="60" width="22" height="110" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="568" y="90" width="22" height="80" rx="2" fill="#4CAF50"/>
            <!-- Jan -->
            <rect x="612" y="40" width="22" height="130" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="634" y="80" width="22" height="90" rx="2" fill="#4CAF50"/>
            <!-- Feb -->
            <rect x="678" y="16" width="22" height="154" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="700" y="90" width="22" height="80" rx="2" fill="#4CAF50"/>
            <!-- Mar -->
            <rect x="744" y="48" width="22" height="122" rx="2" fill="#F39C12" opacity="0.65"/>
            <rect x="766" y="66" width="22" height="104" rx="2" fill="#4CAF50"/>
          </svg>
        </div>
        <div class="line-chart-xlabels">
          <span>Apr</span><span>May</span><span>Jun</span><span>Jul</span>
          <span>Aug</span><span>Sep</span><span>Oct</span><span>Nov</span>
          <span>Dec</span><span>Jan</span><span>Feb</span><span>Mar</span>
        </div>
      </div>
      <p class="spec">Grouped bars: demand at 65% opacity beside sales &middot; 2px rounded top corners &middot; Y-axis: &ldquo;Quantity&rdquo; label rotated &middot; Axis labels: Poppins 0.8rem</p>

      <h3>Matplotlib rcParams</h3>
      <pre><code>import matplotlib.pyplot as plt

plt.rcParams.update({{
    "font.family": "Poppins",
    "font.size": 11,
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#e0e0e0",
    "axes.grid": True,
    "grid.color": "#e0e0e0",
    "grid.linewidth": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "#ffffff",
}})

CW_PALETTE = ["#336699", "#20b0a5", "#42A5F5", "#27AE60",
              "#F39C12", "#C0392B", "#8E44AD", "#17A589"]</code></pre>

      <h3>Do&rsquo;s and Don&rsquo;ts</h3>
      <div class="dos-donts">
        <div class="do">
          <h4>Do</h4>
          <ul>
            <li>Use brand palette in priority order</li>
            <li>Consistent legend placement (top-right)</li>
            <li>Red/green only for status (not categories)</li>
          </ul>
        </div>
        <div class="dont">
          <h4>Don&rsquo;t</h4>
          <ul>
            <li>Use rainbow colormaps</li>
            <li>Mix too many colors (max 6-8 series)</li>
            <li>Use 3D effects or chart borders</li>
          </ul>
        </div>
      </div>
    </section>"""


def _sec_examples(assets: dict) -> str:
    icon_src = assets.get("icon") or ""
    logo_img = (
        f'<img src="{icon_src}" style="height:28px" alt="CW">' if icon_src else "CW"
    )

    return f"""
    <section id="examples">
      <h2>15. Application Gallery</h2>

      <h3>Web App Layout</h3>
      <div class="mockup-frame">
      <div class="example-webapp">
        <div class="ew-sidebar">
          <div class="ew-brand">{logo_img} <strong>CatWing</strong></div>
          <div class="ew-filter">Brand</div>
          <div class="ew-filter">Status</div>
          <div class="ew-filter active">Tissot</div>
        </div>
        <div class="ew-main">
          <div class="ew-header">
            <strong>Global Assortment Review</strong>
            <span>1,247 products &middot; 72% reviewed</span>
          </div>
          <div class="ew-table">
            <div class="ew-th">Product | Status | Revenue | Zone</div>
            <div class="ew-tr">Tissot PRX 35mm | <span class="cw-badge stock badge-mini">STOCK</span> | &euro;12,450 | A</div>
            <div class="ew-tr confirmed">Certina DS Action | <span class="cw-badge stock badge-mini">STOCK</span> | &euro;8,320 | B</div>
          </div>
        </div>
      </div>
      </div>
      <p class="mockup-frame-label">Light mode preview</p>

      <h3>Presentation Slide</h3>
      <div class="example-slide">
        <div class="es-header">
          <span class="wm-cat wm-slide">Cat</span><span class="wm-wing wm-slide">Wing</span>
        </div>
        <div class="es-body">
          <div class="es-title">Inventory Optimization Results</div>
          <div class="es-kpis">
            <div class="es-kpi"><strong>&euro;2.4M</strong><br>Revenue Uplift</div>
            <div class="es-kpi"><strong>-18%</strong><br>Overstock Reduction</div>
            <div class="es-kpi"><strong>95.8%</strong><br>Model Accuracy</div>
          </div>
        </div>
      </div>

      <h3>Email Signature</h3>
      <div class="example-email">
        <div class="ee-row">
          {logo_img}
          <div>
            <strong>Jane Smith</strong><br>
            <span class="ee-meta">Supply Chain Analyst &middot; CatWing</span><br>
            <span class="ee-contact">jane@catwing.ai &middot; +31 6 1234 5678</span>
          </div>
        </div>
      </div>

      <h3>Excel Export Header</h3>
      <div class="example-excel">
        <div class="ex-header">Product | SKU | Status | Revenue | Stock Qty</div>
        <div class="ex-row">Tissot PRX 35mm | T137.210 | STOCK | &euro;12,450 | 24</div>
        <div class="ex-row alt">Certina DS Action | C032.807 | STOCK | &euro;8,320 | 18</div>
        <div class="ex-row confirmed">Swatch Gent | SO29K100 | NOT-STOCK | &euro;1,890 | 3</div>
      </div>

      <h3>Terminal / CLI Output</h3>
      <div class="example-terminal">
        <span class="term-muted">[2026-03-08 14:23:01]</span> <span class="term-blue">CatWing Pipeline v3.2</span><br>
        <span class="term-muted">[2026-03-08 14:23:02]</span> Stage 1: Extract <span class="term-green">OK</span> (1.2s)<br>
        <span class="term-muted">[2026-03-08 14:23:05]</span> Stage 2: Transform &amp; Load <span class="term-green">OK</span> (3.1s)<br>
        <span class="term-muted">[2026-03-08 14:23:12]</span> Stage 3: Enrichment <span class="term-green">OK</span> (7.4s)<br>
        <span class="term-muted">[2026-03-08 14:23:28]</span> Stage 4: ML Predictions <span class="term-green">OK</span> (15.8s)<br>
        <span class="term-muted">[2026-03-08 14:23:30]</span> Stage 5: Monitoring <span class="term-yellow">WARN</span> (2 drift alerts)<br>
        <span class="term-muted">[2026-03-08 14:23:30]</span> Pipeline complete. <span class="term-green">5/5 stages passed.</span>
      </div>
    </section>"""


def _sec_developer(assets: dict) -> str:
    today = date.today().strftime("%Y-%m-%d")
    return f"""
    <section id="developer">
      <h2>16. Developer Reference</h2>

      <h3>CSS Custom Properties</h3>
      <pre><code>:root {{
  --cw-primary: #20b0a5;
  --cw-blue: #336699;
  --cw-dark: #1c1c1c;
  --cw-bg: #f5f7fa;
  --cw-sidebar-bg: linear-gradient(180deg, #f0f5fc 0%, #e8f0f7 100%);
  --cw-header-bg: linear-gradient(135deg, #336699 0%, #20b0a5 100%);
  --status-stock: #4CAF50;
  --status-notstock: #D32F2F;
  --zone-green: #4CAF50;
  --zone-yellow: #FFC107;
  --zone-orange: #FF9800;
  --zone-red: #D32F2F;
  --confirmed-bg: #E8F5E9;
  --confirmed-border: #4CAF50;
  --drift-bg: #FFF3E0;
  --drift-border: #FF9800;
  --radius: 8px;
  --shadow: 0 2px 8px rgba(0,0,0,0.08);
}}</code></pre>

      <h3>Python Constants</h3>
      <pre><code>CW_BLUE = "#336699"
CW_TEAL = "#20b0a5"
CW_PPTX_TEAL = "#27C4CC"
CW_DARK = "#1c1c1c"
CW_BG = "#f5f7fa"
STATUS_STOCK = "#4CAF50"
STATUS_NOTSTOCK = "#D32F2F"
ZONE_COLORS = {{"A": "#4CAF50", "B": "#FFC107", "C": "#FF9800", "D": "#D32F2F"}}</code></pre>

      <h3>PPTX RGBColor Constants</h3>
      <pre><code>from pptx.util import Pt, Inches
from pptx.dml.color import RGBColor

CW_BLUE = RGBColor(0x33, 0x66, 0x99)
CW_TEAL = RGBColor(0x27, 0xC4, 0xCC)
CW_GRAY = RGBColor(0x66, 0x66, 0x66)
CW_DARK = RGBColor(0x33, 0x33, 0x33)</code></pre>

      <h3>Google Fonts Import</h3>
      <pre><code>&lt;link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&amp;family=Outfit:wght@700&amp;display=swap" rel="stylesheet"&gt;</code></pre>

      <h3>Quick-Start Patterns</h3>
      <p class="note">Copy-paste ready. These are the most-used patterns across the app.</p>
      <pre><code>/* Brand gradient button */
.btn-primary {{
  background: linear-gradient(135deg, #336699 0%, #20b0a5 100%);
  color: #fff; border: none; border-radius: 6px;
  padding: 0.5rem 0.8rem; font-weight: 600; cursor: pointer;
}}

/* Status badge */
.badge-stock {{
  background: #4CAF50; color: #fff; border-radius: 4px;
  padding: 2px 8px; font-size: 0.7rem; font-weight: 700;
}}

/* Confirmed row highlight */
.row-confirmed {{
  background: #E8F5E9; border-left: 4px solid #4CAF50;
}}

/* Drift row highlight */
.row-drift {{
  background: #FFF3E0; border-left: 4px solid #FF9800;
}}

/* Card with standard shadow */
.card {{
  background: #fff; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  padding: 1rem;
}}

/* Table header */
.thead {{
  background: linear-gradient(135deg, #336699 0%, #20b0a5 100%);
  color: #fff; font-weight: 600; font-size: 0.8rem;
}}</code></pre>

      <h3>Build</h3>
      <pre><code>cd &lt;repo&gt;/catwing-brand
python tools/build.py                # Build and open in browser
python tools/build.py --no-open      # Build without opening
python tools/build.py --fresh-fonts  # Re-download fonts</code></pre>

      <h3>Logo Assets</h3>
      <pre><code>brand/logo/                       # All logo variants
  catwing_icon_48.png             # Favicon, tiny UI
  catwing_icon_128.png            # App header, sidebar
  catwing_full_600.png            # Vertical lockup (light bg)
  catwing_full_dark_600.png       # Vertical lockup (dark bg)
  catwing_horiz_800x400.png       # Horizontal lockup (light bg)
  catwing_horiz_dark_800x400.png  # Horizontal lockup (dark bg)
  catwing_wordmark_600.png        # Wordmark only
  catwing_icon.ico                # Browser favicon</code></pre>

      <h3>UI &amp; App Design Guide</h3>
      <p>For component specifications, interaction patterns, context-specific color palettes,
      and CSS implementation details, see the <a href="design.html">UI &amp; App Design Guide</a>.</p>

      <h3>Version</h3>
      <p class="note">v{VERSION} &middot; Generated {today} by <code>tools/build.py</code></p>
    </section>"""


def _sec_ui_intro() -> str:
    return """
    <section id="ui-intro" class="hero" style="min-height:auto;padding:3rem 2rem">
      <div class="hero-inner" style="gap:0.8rem">
        <h1 style="font-size:2rem">UI &amp; App Design Guide</h1>
        <p class="hero-tagline" style="font-size:1rem">Implementation-specific design rules for CatWing interfaces</p>
        <p class="hero-sub">For core brand identity, see the <a href="brand.html" style="color:#fff;text-decoration:underline">Brand Identity Guide</a></p>
      </div>
    </section>

    <section id="ui-contexts">
      <h2>1. Design Contexts</h2>

      <p>CatWing interfaces serve two distinct purposes, each requiring different visual treatment.</p>

      <div class="side-by-side">
        <div class="context-card context-card-dark">
          <h4>Website &amp; Marketing</h4>
          <p>Public-facing: catwing.ai, brand guide, presentations, investor materials.
            Dark theme with vivid accents for impact and technical credibility.</p>
          <ul>
            <li>Dark backgrounds (#0f1923)</li>
            <li>Brand gradient headers</li>
            <li>Vivid status colors for visual impact</li>
            <li>Designed for brief, focused engagement</li>
          </ul>
        </div>
        <div class="context-card context-card-light">
          <h4>Admin Applications</h4>
          <p>Internal tools: Assortment Review, dashboards, data browsers.
            Light theme with muted accents for all-day comfort and readability.</p>
          <ul>
            <li>Light backgrounds (#f5f7fa)</li>
            <li>Solid color headers (no gradient)</li>
            <li>Muted status colors to reduce eye strain</li>
            <li>Designed for 8+ hours of daily use</li>
          </ul>
        </div>
      </div>

      <div class="callout">
        <strong>Principle:</strong> Marketing should impress. Admin tools should disappear.
        The interface recedes so the data can speak.
      </div>
    </section>"""


def _sec_ui_palettes() -> str:
    """Side-by-side palette comparison for website vs admin contexts."""

    def _chip(color: str, label: str, text: str = "#fff") -> str:
        border = "border:1px solid #dce3ed;" if color in ("#ffffff", "#f5f7fa") else ""
        return (
            f'<div class="palette-chip">'
            f'<span class="palette-chip-dot" style="background:{color};{border}"></span>'
            f'<span class="palette-chip-label"><strong>{label}</strong>'
            f" <code>{color}</code></span></div>"
        )

    return f"""
    <section id="ui-palettes">
      <h2>2. Color Palettes by Context</h2>

      <p>The <a href="brand.html">Brand Guide</a> defines the canonical CatWing palette.
      Below are the <strong>context-specific adaptations</strong> for each deployment type.</p>

      <h3>Header Treatment</h3>
      <div class="side-by-side">
        <div>
          <div class="header-demo header-demo-gradient">Global Assortment Review</div>
          <p class="spec">Website: Brand gradient (135deg). Eye-catching, establishes identity.</p>
        </div>
        <div>
          <div class="header-demo header-demo-solid">Global Assortment Review</div>
          <p class="spec">Admin: Solid CW Blue. Professional, recedes, zero visual noise.</p>
        </div>
      </div>

      <h3>Status Colors</h3>
      <p class="note">Admin variants are desaturated for comfort during extended use.
      Zone dots remain vivid (10px &mdash; need to be scannable at a glance).</p>

      <div class="side-by-side">
        <div class="palette-card">
          <h4>Website (vivid)</h4>
          {_chip("#4CAF50", "Stock / Success")}
          {_chip("#D32F2F", "Not-Stock / Error")}
          {_chip("#FF9800", "Warning / Drift")}
          {_chip("#42A5F5", "Info")}
        </div>
        <div class="palette-card">
          <h4>Admin (muted)</h4>
          {_chip("#3d8b52", "Stock / Success")}
          {_chip("#c85a54", "Not-Stock / Error")}
          {_chip("#c98a2d", "Warning / Drift")}
          {_chip("#4a7fb5", "Info")}
        </div>
      </div>

      <h3>Full Comparison</h3>
      <table class="spec-table">
        <thead><tr><th>Property</th><th>Website</th><th>Admin</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>Theme</strong></td>
            <td>Dark</td>
            <td>Light</td>
          </tr>
          <tr>
            <td><strong>Background</strong></td>
            <td><span class="chip" style="background:#0f1923"></span> #0f1923</td>
            <td><span class="chip" style="background:#f5f7fa"></span> #f5f7fa</td>
          </tr>
          <tr>
            <td><strong>Surface</strong></td>
            <td><span class="chip" style="background:#1a2332"></span> #1a2332</td>
            <td><span class="chip" style="background:#ffffff;border:1px solid #ddd"></span> #ffffff</td>
          </tr>
          <tr>
            <td><strong>Header</strong></td>
            <td>Gradient (135deg)</td>
            <td>Solid #336699</td>
          </tr>
          <tr>
            <td><strong>Text</strong></td>
            <td><span class="chip" style="background:#e2e8f0"></span> #e2e8f0</td>
            <td><span class="chip" style="background:#1c1c1c"></span> #1c1c1c</td>
          </tr>
          <tr>
            <td><strong>Muted text</strong></td>
            <td><span class="chip" style="background:#94a3b8"></span> #94a3b8</td>
            <td><span class="chip" style="background:#666"></span> #666666</td>
          </tr>
          <tr>
            <td><strong>Border</strong></td>
            <td><span class="chip" style="background:#2a3a4a"></span> #2a3a4a</td>
            <td><span class="chip" style="background:#dce3ed"></span> #dce3ed</td>
          </tr>
          <tr>
            <td><strong>Stock</strong></td>
            <td><span class="chip" style="background:#4CAF50"></span> #4CAF50</td>
            <td><span class="chip" style="background:#3d8b52"></span> #3d8b52</td>
          </tr>
          <tr>
            <td><strong>Not-Stock</strong></td>
            <td><span class="chip" style="background:#D32F2F"></span> #D32F2F</td>
            <td><span class="chip" style="background:#c85a54"></span> #c85a54</td>
          </tr>
          <tr>
            <td><strong>Warning</strong></td>
            <td><span class="chip" style="background:#FF9800"></span> #FF9800</td>
            <td><span class="chip" style="background:#c98a2d"></span> #c98a2d</td>
          </tr>
          <tr>
            <td><strong>Info</strong></td>
            <td><span class="chip" style="background:#42A5F5"></span> #42A5F5</td>
            <td><span class="chip" style="background:#4a7fb5"></span> #4a7fb5</td>
          </tr>
        </tbody>
      </table>

      <h3>Background Tints (Admin)</h3>
      <p class="note">Used for status row highlighting and product labels. Shared across both contexts.</p>
      <div class="tint-grid">
        <div class="tint-chip" style="background:#E8F5E9;border-left:4px solid #4CAF50;color:#2E7D32">Confirmed <code>#E8F5E9</code></div>
        <div class="tint-chip" style="background:#FFF3E0;border-left:4px solid #FF9800;color:#BF360C">Drift <code>#FFF3E0</code></div>
        <div class="tint-chip" style="background:#FFEBEE;border-left:4px solid #D32F2F;color:#B71C1C">Danger <code>#FFEBEE</code></div>
        <div class="tint-chip" style="background:#E3F2FD;border-left:4px solid #42A5F5;color:#1565C0">Info <code>#E3F2FD</code></div>
        <div class="tint-chip" style="background:#E8F5E9;color:#2E7D32">Launch <code>#E8F5E9</code></div>
        <div class="tint-chip" style="background:#ECEFF1;color:#616161">Discontinued <code>#ECEFF1</code></div>
        <div class="tint-chip" style="background:#FFEBEE;color:#C62828">Old <code>#FFEBEE</code></div>
        <div class="tint-chip" style="background:#FFF8E1;color:#BF360C">Gold <code>#FFF8E1</code></div>
      </div>

      <h3>CSS Custom Properties</h3>

      <h4>Website Context</h4>
      <pre><code>:root {{
  --cw-bg: #0f1923;
  --cw-surface: #1a2332;
  --cw-text: #e2e8f0;
  --cw-text-muted: #94a3b8;
  --cw-border: #2a3a4a;
  --cw-header-bg: linear-gradient(135deg, #336699 0%, #20b0a5 100%);
  --status-stock: #4CAF50;
  --status-notstock: #D32F2F;
  --status-warning: #FF9800;
  --status-info: #42A5F5;
}}</code></pre>

      <h4>Admin Context</h4>
      <pre><code>:root {{
  --cw-bg: #f5f7fa;
  --cw-surface: #ffffff;
  --cw-text: #1c1c1c;
  --cw-text-muted: #666666;
  --cw-border: #dce3ed;
  --cw-header-bg: #336699;
  --status-stock: #3d8b52;
  --status-notstock: #c85a54;
  --status-warning: #c98a2d;
  --status-info: #4a7fb5;
}}</code></pre>
    </section>"""


def _sec_ui_reference() -> str:
    """CSS reference section for the UI guide (moved from brand developer section)."""
    return """
    <section id="ui-reference">
      <h2>9. CSS Reference</h2>

      <p>For Python constants, PPTX colors, and build commands, see the
      <a href="resources.html#developer">Brand Guide &sect;Developer Reference</a>.</p>

      <h3>Admin App &mdash; Quick-Start Patterns</h3>
      <pre><code>/* Solid header (admin) */
.app-header {
  background: #336699;
  color: #fff; border-radius: 10px;
  padding: 0.8rem 1.2rem;
}

/* Status badge — muted admin palette */
.badge-stock {
  background: #3d8b52; color: #fff; border-radius: 4px;
  padding: 2px 8px; font-size: 0.7rem; font-weight: 700;
}
.badge-notstock {
  background: #c85a54; color: #fff; border-radius: 4px;
  padding: 2px 8px; font-size: 0.7rem; font-weight: 700;
}

/* Confirmed row highlight */
.row-confirmed {
  background: #E8F5E9; border-left: 4px solid #3d8b52;
}

/* Drift row highlight */
.row-drift {
  background: #FFF3E0; border-left: 4px solid #c98a2d;
}

/* Card */
.card {
  background: #fff; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  padding: 1rem;
}

/* Table header (solid, admin) */
.thead {
  background: #336699;
  color: #fff; font-weight: 600; font-size: 0.8rem;
}</code></pre>

      <h3>Website &mdash; Quick-Start Patterns</h3>
      <pre><code>/* Gradient header (website) */
.site-header {
  background: linear-gradient(135deg, #336699 0%, #20b0a5 100%);
  color: #fff;
}

/* Status badge — vivid website palette */
.badge-stock { background: #4CAF50; }
.badge-notstock { background: #D32F2F; }

/* Dark surface card */
.card {
  background: #1a2332; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  padding: 1rem; color: #e2e8f0;
}</code></pre>

      <h3>Full Admin Custom Properties</h3>
      <pre><code>:root {
  /* Brand */
  --cw-primary: #20b0a5;
  --cw-blue: #336699;
  --cw-dark: #1c1c1c;
  --cw-bg: #f5f7fa;
  --cw-sidebar-bg: linear-gradient(180deg, #f0f5fc 0%, #e8f0f7 100%);
  --cw-header-bg: #336699;

  /* Status (muted for admin) */
  --status-stock: #3d8b52;
  --status-notstock: #c85a54;
  --status-warning: #c98a2d;
  --status-info: #4a7fb5;

  /* Zones (vivid — small dots need contrast) */
  --zone-green: #4CAF50;
  --zone-yellow: #FFC107;
  --zone-orange: #FF9800;
  --zone-red: #D32F2F;

  /* Row highlights */
  --confirmed-bg: #E8F5E9;
  --confirmed-border: #3d8b52;
  --drift-bg: #FFF3E0;
  --drift-border: #c98a2d;
  --sub-row-bg: #f0f4f8;

  /* Layout */
  --radius: 8px;
  --shadow: 0 2px 8px rgba(0,0,0,0.08);
}</code></pre>
    </section>"""


def _sec_home(assets: dict) -> str:
    """Home page hero and card navigation."""
    logo_img = ""
    if assets.get("icon"):
        logo_img = f'<img src="{assets["icon"]}" alt="CatWing" class="home-logo">'

    return f"""
    <div class="home-hero">
      <div class="home-hero-inner">
        {logo_img}
        <h1>CatWing</h1>
        <p>Brand &amp; Design Documentation</p>
      </div>
    </div>

    <div class="home-grid">
      <a href="brand.html" class="home-card">
        <div class="home-card-accent" style="background:linear-gradient(135deg,#336699,#20b0a5)"></div>
        <h3>Brand Identity</h3>
        <p>Philosophy, logo system, color palette, typography, iconography, voice &amp; tone, dark mode guidelines.</p>
        <span class="home-card-meta">7 sections</span>
      </a>
      <a href="design.html" class="home-card">
        <div class="home-card-accent" style="background:#20b0a5"></div>
        <h3>UI &amp; App Design</h3>
        <p>Context-specific palettes for websites and admin apps, components, interactions, state patterns, layout, motion.</p>
        <span class="home-card-meta">7 sections</span>
      </a>
      <a href="resources.html" class="home-card">
        <div class="home-card-accent" style="background:#336699"></div>
        <h3>Resources &amp; Templates</h3>
        <p>Business cards, application gallery, data visualization standards, developer reference and CSS custom properties.</p>
        <span class="home-card-meta">4 sections</span>
      </a>
    </div>

    <div class="home-quickref">
      <h3>Quick Reference</h3>
      <div class="home-colors">
        <div class="home-color"><span class="home-color-dot" style="background:#336699"></span> CW Blue #336699</div>
        <div class="home-color"><span class="home-color-dot" style="background:#20b0a5"></span> CW Teal #20b0a5</div>
        <div class="home-color"><span class="home-color-dot" style="background:#1c1c1c"></span> CW Dark #1c1c1c</div>
        <div class="home-color"><span class="home-color-dot" style="background:#f5f7fa;border:1px solid #dce3ed"></span> CW BG #f5f7fa</div>
        <div class="home-color"><span class="home-color-dot" style="background:#4CAF50"></span> Success #4CAF50</div>
        <div class="home-color"><span class="home-color-dot" style="background:#D32F2F"></span> Error #D32F2F</div>
      </div>
      <p style="margin-top:0.8rem;font-size:0.82rem;color:var(--guide-text-muted)">
        Font: <strong>Poppins</strong> (web) &middot;
        <strong>Outfit Bold</strong> (logo) &middot;
        Gradient: <code>135deg #336699 &rarr; #20b0a5</code>
      </p>
    </div>"""


def _sec_business_cards(assets: dict) -> str:
    """Business card templates section."""
    icon_img = ""
    if assets.get("icon_128") or assets.get("icon"):
        src = assets.get("icon_128") or assets.get("icon")
        icon_img = f'<img src="{src}" alt="CW">'

    return f"""
    <section id="business-cards">
      <h2>Business Cards</h2>

      <p>Standard business card format: 85 &times; 55 mm (3.5 &times; 2 in).
      Gradient accent bar at the top ties to the brand identity.
      Name in Poppins Bold, contact details in CW Blue (light) or CW Teal (dark).</p>

      <h3>Light Variant</h3>
      <div class="biz-cards-grid">
        <div>
          <div class="biz-card light">
            <div class="biz-card-logo">
              {icon_img}
              <span class="biz-card-wm"><span class="wm-cat">Cat</span><span class="wm-wing">Wing</span></span>
            </div>
            <div class="biz-card-info">
              <div class="biz-card-name">Sergi Sergiev</div>
              <div class="biz-card-title">CEO</div>
              <div class="biz-card-contact">
                sergi@catwing.ai<br>
                +359 888 400 290
              </div>
            </div>
          </div>
          <div class="biz-card-variant"><span>Front</span></div>
        </div>

        <div>
          <div class="biz-card biz-card-back light">
            <div class="biz-card-back-content">
              {icon_img}
              <span class="biz-card-wm"><span class="wm-cat">Cat</span><span class="wm-wing">Wing</span></span>
              <div class="biz-card-tagline">Deep-tech AI for Supply Chain</div>
              <div class="biz-card-url light">catwing.ai</div>
            </div>
          </div>
          <div class="biz-card-variant"><span>Back</span></div>
        </div>
      </div>

      <h3>Dark Variant</h3>
      <div class="biz-cards-grid">
        <div>
          <div class="biz-card dark">
            <div class="biz-card-logo">
              {icon_img}
              <span class="biz-card-wm"><span class="wm-cat">Cat</span><span class="wm-wing">Wing</span></span>
            </div>
            <div class="biz-card-info">
              <div class="biz-card-name">Sergi Sergiev</div>
              <div class="biz-card-title">CEO</div>
              <div class="biz-card-contact">
                sergi@catwing.ai<br>
                +359 888 400 290
              </div>
            </div>
          </div>
          <div class="biz-card-variant"><span>Front</span></div>
        </div>

        <div>
          <div class="biz-card biz-card-back dark">
            <div class="biz-card-back-content">
              {icon_img}
              <span class="biz-card-wm"><span class="wm-cat">Cat</span><span class="wm-wing">Wing</span></span>
              <div class="biz-card-tagline">Deep-tech AI for Supply Chain</div>
              <div class="biz-card-url dark">catwing.ai</div>
            </div>
          </div>
          <div class="biz-card-variant"><span>Back</span></div>
        </div>
      </div>

      <h3>Typography Specifications</h3>
      <table class="spec-table">
        <thead><tr><th>Element</th><th>Font</th><th>Size</th><th>Weight</th><th>Color (Light)</th><th>Color (Dark)</th></tr></thead>
        <tbody>
          <tr><td>Wordmark</td><td>Outfit</td><td>16px</td><td>700</td><td>#1a1a2e / #20b0a5</td><td>#ffffff / #20b0a5</td></tr>
          <tr><td>Name</td><td>Poppins</td><td>16px</td><td>700</td><td>#1c1c1c</td><td>#e2e8f0</td></tr>
          <tr><td>Title</td><td>Poppins</td><td>11px</td><td>500</td><td>#666666</td><td>#94a3b8</td></tr>
          <tr><td>Contact</td><td>Poppins</td><td>11px</td><td>400</td><td>#336699</td><td>#20b0a5</td></tr>
        </tbody>
      </table>

      <h3>Construction</h3>
      <ul>
        <li><strong>Size:</strong> 85 &times; 55 mm (standard European business card)</li>
        <li><strong>Bleed:</strong> 3 mm on all sides</li>
        <li><strong>Safe zone:</strong> 5 mm inset from trim edge</li>
        <li><strong>Accent bar:</strong> 4px gradient (#336699 &rarr; #20b0a5) at top edge</li>
        <li><strong>Corner radius:</strong> 3 mm (for rounded-corner print) or 0 (standard cut)</li>
        <li><strong>Logo icon:</strong> 28px height, aligned left with wordmark</li>
      </ul>

      <h3>Print Guidelines</h3>
      <div class="callout">
        <strong>Light variant:</strong> Print on 350gsm uncoated white card stock. Matte or silk finish.
        The gradient bar should be printed in full color (CMYK process).<br><br>
        <strong>Dark variant:</strong> Print on 350gsm coated card stock with matte lamination.
        The dark background (#0f1923) requires good ink coverage &mdash; request a press proof.
      </div>
    </section>"""


# ── HTML Assembly ─────────────────────────────────────────────────────────

# Page registry for wiki navigation
PAGE_NAV = [
    ("index.html", "Home"),
    ("brand.html", "Brand Identity"),
    ("design.html", "UI & App Design"),
    ("resources.html", "Resources"),
]


def _build_page(
    filename: str,
    title: str,
    nav_items: list[tuple[str, str]],
    sections: list[str],
    assets: dict,
    fonts_css: str,
) -> str:
    """Build a wiki page with shared navigation."""
    # Page-level nav (always visible)
    page_links = []
    for href, label in PAGE_NAV:
        cls = ' class="current"' if href == filename else ""
        page_links.append(f'    <a href="{href}"{cls}>{label}</a>')
    pages_html = "\n".join(page_links)

    # Section-level nav (scroll-spy within page)
    section_links = "\n".join(
        f'    <a href="#{id_}">{label}</a>' for id_, label in nav_items
    )

    css_file = BRAND_DIR / "src" / "style.css"
    js_file = BRAND_DIR / "src" / "script.js"
    guide_css = css_file.read_text(encoding="utf-8") if css_file.exists() else ""
    guide_js = js_file.read_text(encoding="utf-8") if js_file.exists() else ""

    font_fallback = ""
    if not fonts_css:
        font_fallback = (
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link href="https://fonts.googleapis.com/css2?'
            "family=Outfit:wght@700&family=Poppins:wght@400;500;600;700"
            '&display=swap" rel="stylesheet">'
        )

    favicon_link = ""
    fav = assets.get("favicon_ico") or assets.get("favicon")
    if fav:
        favicon_link = f'<link rel="icon" href="{fav}">'

    # Build nav sidebar
    nav_content = f"""
    <div class="nav-pages">
{pages_html}
    </div>"""

    if nav_items:
        nav_content += f"""
    <hr class="nav-divider">
    <span class="nav-section-label">On this page</span>
    <div class="nav-sections">
{section_links}
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CatWing &mdash; {title}</title>
  {favicon_link}
  {font_fallback}
  <style>
{fonts_css}
{guide_css}
  </style>
</head>
<body>
  <button class="nav-toggle" aria-label="Toggle navigation">&#9776;</button>
  <nav class="guide-nav">
    <h2>CatWing</h2>
{nav_content}
    <div class="theme-toggle-wrap">
      <button class="theme-toggle" id="theme-toggle" aria-label="Toggle dark mode">&#9790; Dark</button>
    </div>
  </nav>
  <main class="guide-main">
{"".join(sections)}
  </main>
  <script>
{guide_js}
  </script>
</body>
</html>"""


def build_home_html(assets: dict, fonts_css: str) -> str:
    """Build the wiki home page."""
    return _build_page(
        filename="index.html",
        title="Documentation",
        nav_items=[],
        sections=[_sec_home(assets)],
        assets=assets,
        fonts_css=fonts_css,
    )


def build_brand_html(assets: dict, fonts_css: str) -> str:
    """Build the Brand Identity Guide page."""
    nav_items = [
        ("philosophy", "Philosophy"),
        ("logos", "Logo System"),
        ("colors", "Color System"),
        ("typography", "Typography"),
        ("iconography", "Iconography"),
        ("voice", "Voice & Tone"),
        ("darkmode", "Dark Mode"),
    ]
    sections = [
        _sec_cover(assets),
        _sec_philosophy(),
        _sec_logos(assets),
        _sec_colors(),
        _sec_typography(),
        _sec_iconography(),
        _sec_voice(),
        _sec_darkmode(),
    ]
    return _build_page(
        filename="brand.html",
        title="Brand Identity",
        nav_items=nav_items,
        sections=sections,
        assets=assets,
        fonts_css=fonts_css,
    )


def build_design_html(assets: dict, fonts_css: str) -> str:
    """Build the UI & App Design Guide page."""
    nav_items = [
        ("ui-contexts", "Design Contexts"),
        ("ui-palettes", "Color Palettes"),
        ("components", "Components"),
        ("interactions", "Interactions"),
        ("states", "State Patterns"),
        ("layout", "Layout & Spacing"),
        ("motion", "Motion"),
    ]
    sections = [
        _sec_ui_intro(),
        _sec_ui_palettes(),
        _sec_components(),
        _sec_interactions(),
        _sec_states(),
        _sec_layout(),
        _sec_motion(),
    ]
    return _build_page(
        filename="design.html",
        title="UI & App Design",
        nav_items=nav_items,
        sections=sections,
        assets=assets,
        fonts_css=fonts_css,
    )


def build_resources_html(assets: dict, fonts_css: str) -> str:
    """Build the Resources & Templates page."""
    nav_items = [
        ("business-cards", "Business Cards"),
        ("examples", "App Gallery"),
        ("dataviz", "Data Viz"),
        ("developer", "Developer Ref"),
    ]
    sections = [
        _sec_business_cards(assets),
        _sec_examples(assets),
        _sec_dataviz(),
        _sec_developer(assets),
    ]
    return _build_page(
        filename="resources.html",
        title="Resources & Templates",
        nav_items=nav_items,
        sections=sections,
        assets=assets,
        fonts_css=fonts_css,
    )


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Build CatWing Documentation Wiki")
    parser.add_argument(
        "--fresh-fonts", action="store_true", help="Re-download fonts from Google"
    )
    parser.add_argument(
        "--no-open", action="store_true", help="Don't open browser after build"
    )
    args = parser.parse_args()

    print(f"Building CatWing Documentation v{VERSION}...")
    print()

    print("Loading assets:")
    assets = _load_assets()
    print()

    print("Loading fonts:")
    fonts_css = _fetch_and_embed_fonts(fresh=args.fresh_fonts)
    print()

    builders = [
        ("Home", "home", build_home_html),
        ("Brand Identity", "brand", build_brand_html),
        ("UI & App Design", "design", build_design_html),
        ("Resources & Templates", "resources", build_resources_html),
    ]

    for label, key, builder in builders:
        path = PAGES[key]
        html = builder(assets, fonts_css)
        path.write_text(html, encoding="utf-8")
        kb = path.stat().st_size / 1024
        print(f"  {label}: {path.name} ({kb:.0f} KB)")

    print()

    if not args.no_open:
        webbrowser.open(PAGES["home"].as_uri())
        print("Done! Opened home page in browser.")
    else:
        print("Done!")


if __name__ == "__main__":
    main()
