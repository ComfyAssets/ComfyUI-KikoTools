"""ComfyUI loads the pack as ``custom_nodes/kikotools``, not as the
``kikotools`` package, so modules inside it must import each other relatively."""

import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "kikotools"
ABSOLUTE = re.compile(r"^(from|import) kikotools\b", re.MULTILINE)


def test_package_modules_use_relative_imports():
    offenders = [
        str(path.relative_to(PACKAGE.parent))
        for path in sorted(PACKAGE.rglob("*.py"))
        if ABSOLUTE.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
