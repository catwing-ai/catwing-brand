# catwing-brand

Canonical CatWing brand identity: colors, typography, logo variants, iconography, voice, components, interaction patterns. Built as four self-contained HTML pages.

## View online

GitHub Pages: **https://catwing.github.io/catwing-brand/** (deployed on every push to `main` via `.github/workflows/pages.yml`).

- `index.html` — Wiki landing
- `brand.html` — Brand Identity Guide
- `design.html` — UI & App Design Guide
- `resources.html` — Templates & downloads

## Build locally

Requires Python 3.10+ (no third-party deps; uses only stdlib + a one-time Google Fonts fetch).

```bash
python build.py                  # build + open in browser
python build.py --no-open        # build only
python build.py --fresh-fonts    # force re-download of Google Fonts cache
```

Outputs land next to `build.py` and are gitignored. Each page embeds all fonts and logos as base64 — open the file directly via `file://` and it renders offline with no network access.

## Layout

See [AGENTS.md](./AGENTS.md) for the full contract (rules for agents, asset coupling, verification).

## Skills

- `.claude/skills/brand-check/` — lint a UI surface for off-brand colors, typography, logo misuse
- `.claude/skills/brand-asset/` — inline color tokens + logo path reference for agent context

## Sibling repos

- [`catwing`](../catwing) — main app + pipeline
- [`catwing-agent-infra`](../catwing-agent-infra) — agent tooling, installers, plugin packaging
- [`catwing-rtk`](../catwing-rtk) — Rust Token Killer source
