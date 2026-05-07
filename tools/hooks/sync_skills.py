"""Asymmetric mirror: .agents/skills/ -> .claude/skills/.

.agents/skills/ is the canonical skills location (Codex auto-discovers).
.claude/skills/ is a committed mirror so Claude Code sees the same skills
without OS-level symlinks. Both directories are tracked by git.

Direct edits to .claude/skills/ are rejected with a redirect message,
unless escape-hatch ALLOW_CLAUDE_SKILLS_EDIT=1 is set.

Exit code 0 = OK. Exit code 1 = rejected.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from contextlib import suppress
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_SKILLS = REPO_ROOT / ".agents" / "skills"
CLAUDE_SKILLS = REPO_ROOT / ".claude" / "skills"
ESCAPE_HATCH = "ALLOW_CLAUDE_SKILLS_EDIT"


def _file_map(root: Path) -> dict[str, str]:
    """Return {relative_path: "<mode_octal>:<sha256>"} for files under root."""
    out: dict[str, str] = {}
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        mode = oct(path.stat().st_mode & 0o777)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        out[rel] = f"{mode}:{digest}"
    return out


def _check_no_symlinks(root: Path) -> list[str]:
    out: list[str] = []
    if not root.exists():
        return out
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            out.append(path.relative_to(REPO_ROOT).as_posix())
    return out


def _staged_paths_under(prefix: str) -> set[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {line for line in result.stdout.splitlines() if line.startswith(prefix)}


def _resync_claude_from_agents() -> None:
    """Mirror .agents/skills/ -> .claude/skills/ exactly. Stage the result."""
    if CLAUDE_SKILLS.exists():
        shutil.rmtree(CLAUDE_SKILLS)
    if AGENTS_SKILLS.exists():
        shutil.copytree(AGENTS_SKILLS, CLAUDE_SKILLS, symlinks=False)
        for src in AGENTS_SKILLS.rglob("*"):
            if not src.is_file() or src.is_symlink():
                continue
            dst = CLAUDE_SKILLS / src.relative_to(AGENTS_SKILLS)
            with suppress(OSError, NotImplementedError):
                dst.chmod(src.stat().st_mode & 0o777)
    subprocess.run(["git", "add", str(CLAUDE_SKILLS)], cwd=REPO_ROOT, check=True)


def main() -> int:
    symlink_violations = _check_no_symlinks(AGENTS_SKILLS) + _check_no_symlinks(
        CLAUDE_SKILLS
    )
    if symlink_violations:
        print(
            "ERROR: symlinks found under .agents/skills/ or .claude/skills/:\n"
            + "\n".join(f"  {p}" for p in symlink_violations),
            file=sys.stderr,
        )
        return 1

    agents_map = _file_map(AGENTS_SKILLS)
    claude_map = _file_map(CLAUDE_SKILLS)
    if agents_map == claude_map:
        return 0

    agents_staged = _staged_paths_under(".agents/skills/")
    claude_staged = _staged_paths_under(".claude/skills/")

    if claude_staged and not agents_staged and not os.environ.get(ESCAPE_HATCH):
        print(
            "ERROR: .claude/skills/ is a generated mirror — edit "
            ".agents/skills/ instead, then `python tools/hooks/sync_skills.py`.\n"
            f"To override (rare), set {ESCAPE_HATCH}=1 in env.",
            file=sys.stderr,
        )
        return 1

    _resync_claude_from_agents()
    print(
        "info: .claude/skills/ regenerated from .agents/skills/ and staged.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
