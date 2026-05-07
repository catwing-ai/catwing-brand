---
name: brand-asset
description: Inline reference for CatWing brand tokens — colors, typography, logo paths, voice — for agents building or reviewing UI. Use to look up canonical hex values, font stacks, or logo asset filenames without re-reading the brand guide HTML.
effort: low
---

You are answering an agent's question about CatWing brand tokens. Give them the canonical value and the source-of-truth path; do not invent values, do not fall back to memory.

This skill is a flat reference card. The full brand guide is `brand.html` (compiled from `build.py`, deployed at https://catwing.github.io/catwing-brand/). When the question is broader than a single token, point the asker there.

## Colors (canonical from `build.py::COLORS`)

### Primary

| Name | Hex | Role |
|------|-----|------|
| CW Blue | `#336699` | Primary brand, headers, table backgrounds |
| CW Teal | `#20b0a5` | Accent, CTAs, secondary brand element |
| CW Presentation Teal | `#27C4CC` | PPTX wordmark accent (lighter variant) |
| CW Dark | `#1c1c1c` | Body text |
| CW Background | `#f5f7fa` | Page backgrounds |
| Logo Charcoal | `#1a1a2e` | Logo on light backgrounds |
| Dark Mode BG | `#0f1923` | Dark surfaces |

### Semantic

| Name | Hex | Role |
|------|-----|------|
| Success | `#4CAF50` | Positive status, confirmations |
| Error | `#D32F2F` | Negative status, danger actions |
| Warning | _(see `brand.html`)_ | Caution states |
| Info | _(see `brand.html`)_ | Informational |

For the full palette including tints, shades, and neutral scales, open `brand.html` § "Color System" or grep `build.py::COLORS`.

## Logo assets (relative to repo root `logo/`)

| Key | Filename | Use |
|-----|----------|-----|
| `icon_128` | `catwing_icon_128.png` | App icon at 128px |
| `full_light` | `catwing_full_600.png` | Full logo on light bg, 600px |
| `full_dark` | `catwing_full_dark_600.png` | Full logo on dark bg, 600px |
| `horiz_light` | `catwing_horiz_800x400.png` | Horizontal lockup, light bg |
| `horiz_dark` | `catwing_horiz_dark_800x400.png` | Horizontal lockup, dark bg |
| `wordmark` | `catwing_wordmark_600.png` | Wordmark only |
| `favicon_ico` | `catwing_icon.ico` | Multi-resolution favicon |
| `icon` | `streamlit_logo.png` | Bundled streamlit-app icon |
| `favicon` | `streamlit_favicon.ico` | Bundled streamlit favicon |

Higher-resolution variants (`*_1200.png`) and small sizes (`*_48.png`, `*_64.png`, `*_300.png`) live in the same folder for cases where 600px is wrong.

## Typography

Canonical stacks live in `style.css` and are mirrored in `build.py`. Open `brand.html` § "Typography" for the specimen sheet. Do not invent fallbacks — if you need a stack for Tailwind config or a CSS file, copy from `style.css`.

## Voice

See `brand.html` § "Voice" for tone rules (B2B supply-chain SaaS register: data-dense, precise, no marketing fluff). When answering microcopy questions, paraphrase from that section rather than improvising.

## When asked something this card does not cover

Tell the asker: "Open `brand.html` § <section>" and name the section. Do not guess. Do not pull from training data. The brand guide is the source of truth; this skill is a fast-lookup index, not a substitute.
