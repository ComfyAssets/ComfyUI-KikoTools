#!/usr/bin/env python3
"""Print the CHANGELOG.md section for a release tag.

Usage: changelog_section.py v1.6.0 [CHANGELOG.md]

Tag v1.6.0 matches the "## 1.6.0" heading; the section runs to the next "## "
heading. Exits 1 with a message on stderr when there is no such section.
"""

import sys
from pathlib import Path


def changelog_section(changelog: str, tag: str) -> str:
    version = tag.removeprefix("v")
    lines = changelog.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip() == f"## {version}"), None
    )
    if start is None:
        raise ValueError(f"CHANGELOG.md has no '## {version}' section for tag {tag}")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    body = "\n".join(lines[start + 1 : end]).strip()
    if not body:
        raise ValueError(f"CHANGELOG.md section '## {version}' is empty")
    return body + "\n"


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(sys.argv[2] if len(sys.argv) == 3 else "CHANGELOG.md")
    try:
        sys.stdout.write(
            changelog_section(path.read_text(encoding="utf-8"), sys.argv[1])
        )
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
