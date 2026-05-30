<p align="center">
  <img src="https://raw.githubusercontent.com/catwing-ai/catwing-brand/main/logo/catwing_icon_128.png" alt="CatWing logo" width="96" />
</p>

<h1 align="center">Catwing Brand</h1>

<p align="center">Canonical CatWing brand identity — colors, typography, logo variants, iconography, voice, components, interaction patterns. Built as four self-contained HTML pages.</p>

## 🌐 View Online

GitHub Pages: **https://catwing-ai.github.io/catwing-brand/** (deployed on every push to `main` via `.github/workflows/pages.yml`).

Published for reference; no open-source license is granted.

- `index.html` — Wiki landing
- `brand.html` — Brand Identity Guide
- `design.html` — UI & App Design Guide
- `resources.html` — Templates & downloads
- `tokens.json`, `tokens.css` — machine-readable token export (for cross-repo agents and Tailwind/CSS-var configs)

## 🛠️ Build Locally

Requires Python 3.10+ (no third-party deps; uses only stdlib + a one-time Google Fonts fetch).

```bash
python tools/build.py                  # build + open in browser
python tools/build.py --no-open        # build only
python tools/build.py --fresh-fonts    # force re-download of Google Fonts cache
```

Outputs land at the repo root and are gitignored. Each page embeds all fonts and logos as base64 — open the file directly via `file://` and it renders offline with no network access.

## 📁 Project Structure

| Path | Purpose |
|------|---------|
| `tools/build.py` | Compiles the four HTML pages |
| `src/style.css`, `src/script.js` | Wiki page styling + interaction |
| `logo/` | Logo masters, raster variants, generator scripts |
| `docs/` | Project documentation |
| `.agents/skills/` | Canonical skill prompts (Codex auto-discovers) |
| `.claude/skills/` | Mirror of `.agents/skills/` (auto-synced; never edit directly) |
| `.github/workflows/pages.yml` | CI build + deploy to GitHub Pages |

## 🤖 For Agents

Start with [`AGENTS.md`](../AGENTS.md) — repo rules, build flow, file/folder limits, cross-repo consumption.

**Token lookup recipe** (any sibling repo / agent context):

```bash
# Programmatic — fetch the latest published tokens
curl -fsSL https://catwing-ai.github.io/catwing-brand/tokens.json
curl -fsSL https://catwing-ai.github.io/catwing-brand/tokens.css

# Human-readable — open the brand guide
open https://catwing-ai.github.io/catwing-brand/brand.html
```

**Skills** (canonical at [`.agents/skills/`](../.agents/skills/), mirrored to `.claude/skills/`):

- [`brand-check`](../.agents/skills/brand-check/SKILL.md) — lint a UI surface for off-brand colors, typography, logo misuse
- [`brand-asset`](../.agents/skills/brand-asset/SKILL.md) — inline color tokens, font stacks, logo paths for agent context
