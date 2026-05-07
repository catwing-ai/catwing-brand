"""Read-only parity guard between .agents/skills/ and .claude/skills/.

Runs on EVERY commit. Catches drift that the file-pattern-filtered
sync_skills hook misses (escape-hatch leftovers, manual edits via another
tool, mode-bit drift, symlinks introduced into the tree).

Failure is actionable: does NOT auto-resync. Run
`python tools/hooks/sync_skills.py` to fix.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_skills import (  # noqa: E402
    AGENTS_SKILLS,
    CLAUDE_SKILLS,
    ESCAPE_HATCH,
    _check_no_symlinks,
    _file_map,
)


def main() -> int:
    symlinks = _check_no_symlinks(AGENTS_SKILLS) + _check_no_symlinks(CLAUDE_SKILLS)
    if symlinks:
        print(
            "ERROR: symlinks found under .agents/skills/ or .claude/skills/:\n"
            + "\n".join(f"  {p}" for p in symlinks),
            file=sys.stderr,
        )
        return 1

    agents_map = _file_map(AGENTS_SKILLS)
    claude_map = _file_map(CLAUDE_SKILLS)
    if agents_map == claude_map:
        return 0

    only_agents = sorted(set(agents_map) - set(claude_map))
    only_claude = sorted(set(claude_map) - set(agents_map))
    differing = sorted(
        path
        for path in set(agents_map) & set(claude_map)
        if agents_map[path] != claude_map[path]
    )

    msg = ["ERROR: .agents/skills/ and .claude/skills/ have drifted."]
    if only_agents:
        msg.append(f"  Only in .agents/skills/ ({len(only_agents)}):")
        msg.extend(f"    + {p}" for p in only_agents[:10])
        if len(only_agents) > 10:
            msg.append(f"    ... and {len(only_agents) - 10} more")
        msg.append("")
    if only_claude:
        msg.append(f"  Only in .claude/skills/ ({len(only_claude)}):")
        msg.extend(f"    + {p}" for p in only_claude[:10])
        if len(only_claude) > 10:
            msg.append(f"    ... and {len(only_claude) - 10} more")
        msg.append("")
    if differing:
        msg.append(f"  Differing content/mode ({len(differing)}):")
        msg.extend(f"    ~ {p}" for p in differing[:10])
        if len(differing) > 10:
            msg.append(f"    ... and {len(differing) - 10} more")
        msg.append("")
    msg.append(
        "Fix: edit the canonical .agents/skills/ tree, then "
        "`python tools/hooks/sync_skills.py`."
    )
    msg.append(
        "If .claude/skills/ has the correct state and .agents/ is stale, "
        "`cp -r .claude/skills/. .agents/skills/` then commit."
    )
    msg.append(f"(Hard override: {ESCAPE_HATCH}=1)")
    print("\n".join(msg), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
