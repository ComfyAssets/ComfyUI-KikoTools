#!/usr/bin/env python3
"""Sort a change by the files it touches, so CI tests only what can break (#118).

Two classes, decided from an allowlist:

- ``inert``: every file is one that no test and no shipped code reads (the
  Markdown documents at the root, ``docs/``, the example documentation, the
  funding file and the issue and pull request templates). No test job runs.
- ``code``: anything else. A file that is not listed is code, and so is every
  case of doubt: no files, an unknown event, a range git cannot read.

No test here reads a document's content: ``tests/unit/test_package_contents.py``
only matches path names against ``.comfyignore``. ``examples/workflows/`` is
code, because those files ship to users as release assets. To add a file to
the list, first check that no test and no shipped code opens it.

Usage:

``change_class.py``
    Prints ``class=<inert|code>`` for the workflow's ``$GITHUB_OUTPUT``, from
    ``EVENT_NAME``, ``BASE_SHA`` and ``HEAD_SHA``. A pull request is compared
    with its merge base, so commits that landed on main meanwhile do not
    count; a push is compared end to end.

``change_class.py --unless-inert <command...>``
    The pre-push hooks: runs the command unless pre-commit's pushed range
    (``PRE_COMMIT_FROM_REF``..``PRE_COMMIT_TO_REF``) is inert, and exits
    with the command's code.
"""

import os
import subprocess
import sys
from typing import Iterable, Optional

INERT_FILES = frozenset(
    {
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        "TESTING.md",
        "CLAUDE.md",
        "AGENTS.md",
        ".github/FUNDING.yml",
        ".github/pull_request_template.md",
    }
)
INERT_FOLDERS = ("docs/", "examples/documentation/", ".github/ISSUE_TEMPLATE/")

RANGE_EVENTS = frozenset({"pull_request", "push"})
ENVIRONMENT = frozenset(
    {
        "EVENT_NAME",
        "BASE_SHA",
        "HEAD_SHA",
        "PRE_COMMIT_FROM_REF",
        "PRE_COMMIT_TO_REF",
    }
)


def classify(paths: Iterable[str]) -> str:
    """``inert`` or ``code`` for the repository paths of one change."""
    found = "code"
    for path in paths:
        if path not in INERT_FILES and not path.startswith(INERT_FOLDERS):
            return "code"
        found = "inert"
    return found


def changed_paths(base: str, head: str, three_dot: bool) -> Optional[list[str]]:
    """Paths that differ between two commits, or None when git cannot say.

    Renames are listed under both names, so a file moved onto a listed name
    still counts as the code file it was.
    """
    if not base or not head or not base.strip("0") or not head.strip("0"):
        return None
    span = f"{base}...{head}" if three_dot else f"{base}..{head}"
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--no-renames", "-z", span, "--"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return [path for path in result.stdout.split("\0") if path]


def class_of_range(base: str, head: str, three_dot: bool = False) -> str:
    paths = changed_paths(base, head, three_dot)
    if paths is None:
        return "code"
    for path in paths:
        print(f"changed: {path}", file=sys.stderr)
    return classify(paths)


def main(argv: list[str]) -> int:
    if argv[:1] == ["--unless-inert"]:
        found = class_of_range(
            os.environ.get("PRE_COMMIT_FROM_REF", ""),
            os.environ.get("PRE_COMMIT_TO_REF", ""),
        )
        if found == "inert":
            print("Skipped: this push only changes inert files (tools/ci).")
            return 0
        return subprocess.run(argv[1:], check=False).returncode
    event = os.environ.get("EVENT_NAME", "")
    found = "code"
    if event in RANGE_EVENTS:
        found = class_of_range(
            os.environ.get("BASE_SHA", ""),
            os.environ.get("HEAD_SHA", ""),
            three_dot=event == "pull_request",
        )
    print(f"class={found}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
