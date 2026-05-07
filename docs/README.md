<h1 align="center">Catwing Brand</h1>

<p align="center">Canonical CatWing brand identity — colors, typography, logo variants, iconography, voice, components, interaction patterns. Built as four self-contained HTML pages.</p>

## 🌐 View Online

GitHub Pages: **https://catwing-repo.github.io/catwing-brand/** (deployed on every push to `main` via `.github/workflows/pages.yml`).

- `index.html` — Wiki landing
- `brand.html` — Brand Identity Guide
- `design.html` — UI & App Design Guide
- `resources.html` — Templates & downloads

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

## 🤖 Skills

- `brand-check` — lint a UI surface for off-brand colors, typography, logo misuse
- `brand-asset` — inline color tokens + logo path reference for agent context
