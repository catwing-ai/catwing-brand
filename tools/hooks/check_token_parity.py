"""Drift guard: every hex literal in src/style.css must trace to build.py.

Resolves the AGENTS.md "Known drift" item: src/style.css and tools/build.py
both encode color values; the brand guide is the source of truth, but a
stylesheet change without a tools/build.py::COLORS update silently diverges.

This hook fails the commit if a hex appears in src/style.css that isn't in
COLORS / TINTS / GRADIENTS. Pure white (#ffffff / #fff) and pure black
(#000000 / #000) are allowed — they're CSS absolutes, not brand tokens.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STYLE_CSS = REPO / "src" / "style.css"
BUILD_PY = REPO / "tools" / "build.py"

ALLOWED_ABSOLUTES = {"#ffffff", "#000000"}

# Pre-existing orphan hexes in src/style.css. These are wiki-chrome / dark-theme
# / code-block colors that should eventually be promoted to COLORS but aren't
# yet. The hook fails on any NEW orphan (not in this set) so the debt ratchets
# down — never up. Retire entries by promoting the value to COLORS, then
# removing it from this set.
BASELINE_ORPHANS = {
    "#0d1117", "#0d1520", "#0d1620", "#1a2332", "#1a2a3c", "#1a2d3d",
    "#1a332a", "#1e293b", "#1e2d3d", "#243244", "#2a3a4a", "#2a5580",
    "#331a1a", "#33291a", "#3a4a5a", "#555555", "#58a6ff", "#64748b",
    "#666666", "#66bb6a", "#777777", "#7a8a9a", "#7aafcc", "#7b1fa2",
    "#7dd3fc", "#888888", "#8899aa", "#90caf9", "#94a3b8", "#999999",
    "#a5d6a7", "#b2f0f3", "#c9d1d9", "#cdd5e0", "#ce93d8", "#dbeaf5",
    "#dce3ed", "#e0e0e0", "#e2e8f0", "#e8e8e8", "#e8edf4", "#ef5350",
    "#ef9a9a", "#f0f0f0", "#f0f3f7", "#f0f4f8", "#f8f9fb", "#ffa726",
    "#ffcdd2", "#ffd699",
}

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _expand(hex_value: str) -> str:
    """Normalize to lowercase 6-digit form. #fff → #ffffff, #ffff → #ffffff (drop alpha for compare)."""
    h = hex_value.lower()
    if len(h) == 4:  # #rgb
        return "#" + "".join(ch * 2 for ch in h[1:])
    if len(h) == 5:  # #rgba — drop alpha
        return "#" + "".join(ch * 2 for ch in h[1:4])
    if len(h) == 9:  # #rrggbbaa — drop alpha
        return h[:7]
    return h


def _load_canonical() -> set[str]:
    spec = importlib.util.spec_from_file_location("brand_build", BUILD_PY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BUILD_PY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    canonical: set[str] = set()
    for info in module.COLORS.values():
        canonical.add(_expand(info["hex"]))
    for triple in module.TINTS.values():
        for value in triple.values():
            canonical.add(_expand(value))
    for info in module.GRADIENTS.values():
        for match in HEX_RE.finditer(info.get("css", "")):
            canonical.add(_expand(match.group(0)))
    for palette in (module.ADMIN_COLORS, module.WEBSITE_COLORS):
        for value in palette.values():
            canonical.add(_expand(value))
    return canonical


def main() -> int:
    if not STYLE_CSS.exists():
        print(f"ERROR: {STYLE_CSS} not found.", file=sys.stderr)
        return 1
    canonical = _load_canonical()
    canonical |= {_expand(h) for h in ALLOWED_ABSOLUTES}
    canonical |= {_expand(h) for h in BASELINE_ORPHANS}

    found: dict[str, list[int]] = {}
    for lineno, line in enumerate(STYLE_CSS.read_text(encoding="utf-8").splitlines(), 1):
        for match in HEX_RE.finditer(line):
            normalized = _expand(match.group(0))
            if normalized not in canonical:
                found.setdefault(normalized, []).append(lineno)

    if not found:
        return 0

    msg = [
        "ERROR: src/style.css uses NEW hex literals not in tools/build.py.",
        "Every brand color must be registered in COLORS / TINTS / GRADIENTS first.",
        "(Pre-existing orphans are tracked in BASELINE_ORPHANS — only new ones fail.)",
        "",
    ]
    for hex_value in sorted(found):
        lines = found[hex_value]
        preview = ", ".join(str(n) for n in lines[:5])
        if len(lines) > 5:
            preview += f", … ({len(lines)} total)"
        msg.append(f"  {hex_value}  src/style.css:{preview}")
    msg.append("")
    msg.append(
        "Fix: add the value to tools/build.py::COLORS (with role/group), "
        "rebuild, then re-stage src/style.css."
    )
    print("\n".join(msg), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
