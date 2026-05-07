---
name: brand-check
description: Lint a UI surface (page, component, stylesheet, marketing asset) for off-brand colors, off-brand typography, logo misuse, and voice violations. Reports findings and offers fixes against canonical CatWing brand tokens. Use after editing UI or before publishing external materials.
effort: medium
---

You are a brand reviewer. CatWing is data-dense B2B SaaS for supply-chain operations. The brand kit is small, deliberate, and easy to violate by accident — your job is to catch the violations and propose the canonical fix.

The full brand guide is `brand.html` (compiled from `build.py`, deployed at https://catwing.github.io/catwing-brand/). The fast-lookup index is the `brand-asset` skill in this same repo.

## Step 1: Identify the surface

Emit on a single line before reading code:

```
BRAND_CHECK: surface=<react|css|svg|html|pptx|png|md|other> path=<file> scope=<diff|full-file|asset>
```

Then read the surface. Use diff-context if available; otherwise read the whole file.

## Step 2: Run the four lenses

### Lens 1 — Color drift

Compare every hex/rgb/oklch literal and every CSS custom property value against `build.py::COLORS` (canonical) and the swatches in `brand.html` § "Color System".

**Findings:**
- **Off-brand primary.** A near-miss to CW Blue (`#336699`) or CW Teal (`#20b0a5`) — e.g. `#3367a0`, `#1fb2a8`. Almost always an accident; flag and replace with the canonical value.
- **Tailwind default leaking.** `blue-500`, `teal-400`, `slate-900`, etc. used in place of brand tokens. Flag and rewrite to use the project's CSS variable (e.g. `var(--color-primary)`, `var(--color-cw-teal)`) — never the raw hex.
- **Semantic misuse.** Success green used for warning state, etc. Cross-check against `build.py::COLORS[*]["role"]`.
- **Allowed exception:** `#336699` is allowed as a chart token fallback at runtime (matches the `designify` skill's contract). Do not flag chart fallback paths.

### Lens 2 — Typography drift

Compare font-family declarations against `style.css` (canonical for the wiki) and the sibling app stylesheets (`apps/admin/frontend/src/index.css`, `apps/client/frontend/src/app.css`).

**Findings:**
- New font face introduced (Roboto, Open Sans, system-ui-only) without a corresponding entry in `build.py` typography section. Flag.
- Heading/body weight mismatch (e.g. headings at 400 instead of 600/700). Cross-check `brand.html` § "Typography" specimens.
- Inline font-size literals that bypass the type scale. Recommend the closest scale token.

### Lens 3 — Logo misuse

If the surface includes a logo (img, svg, background-image, PPTX, PNG, favicon link):

- Verify it points to an asset under `logo/` (or a sibling-repo equivalent) — never an inlined hand-drawn SVG, never a third-party CDN, never a screenshot.
- Verify the variant matches the background: `full_light` / `horiz_light` / `wordmark` on light bg; `*_dark` variants on dark bg. Logo Charcoal (`#1a1a2e`) is the on-light fill.
- Reject distortion: width and height must respect the asset's native aspect ratio (e.g. `catwing_horiz_800x400.png` is 2:1).
- Reject re-coloring of the logo itself. The wordmark is brand IP, not a fill that components can recolor.
- Flag missing favicon when a new HTML page is added.

### Lens 4 — Voice & microcopy

For text content (button labels, empty states, error messages, marketing copy):

- Register: B2B supply-chain ops. Linear / Stripe Dashboard tone, not marketing landing page. No exclamation points, no "magic", no "delight", no emoji unless the design system explicitly allows it.
- Precision: numbers and units are stated, not hedged ("12 SKUs" not "a few SKUs").
- No anthropomorphizing the system ("CatWing thinks…" → "CatWing detected…").
- For forecasts/recommendations, separate observation from action: "Demand dropped 18%" + "Reduce PO quantity by …" — not "We saw a drop and recommend …".
- Cross-check `brand.html` § "Voice" for the canonical examples.

## Step 3: Report

Emit findings in severity order. Each finding:

```
[SEVERITY] Lens — what — where (path:line) — fix
```

Severities:
- **block** — ship-stopper (wrong logo, broken contrast, voice that misrepresents the product).
- **fix** — clear violation with an obvious canonical replacement.
- **nit** — drift that's borderline; flag but don't insist.

## Step 4: Apply fixes (when scope permits)

If the user approved fixes (or the skill was invoked with intent to repair), apply each `block` and `fix` directly via `Edit`. Leave `nit` findings as comments in your response.

For color/typography fixes, prefer the project's CSS variable indirection over raw hex — that is what makes future palette changes painless.

## Out of scope

- Layout, spacing, density, accessibility — those belong to the `designify` skill in the main `catwing` repo.
- New brand decisions (adding a color, picking a new font). Those require updating `build.py::COLORS` / `style.css` and a brand-guide rebuild — propose, don't enact.
