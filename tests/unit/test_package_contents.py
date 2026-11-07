"""What the Registry package leaves out.

``comfy node publish`` zips the tracked files minus ``.comfyignore``. These checks
hold the two ways that can go wrong: a development folder creeping back into the
download, or a rule that drops something ComfyUI needs at run time. An unanchored
``tools/`` rule did the second for 1.2.0 to 1.3.1: it also matched kikotools/tools/,
so those packages shipped without their nodes.
"""

import ast
import fnmatch
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRS = ("kikotools", "web")
DEVELOPMENT = (
    "tests/unit/test_package_contents.py",
    "scripts/run_mypy.sh",
    "tools/testing/package.json",
    "docs/ui-migration.md",
    "examples/workflows/display_text_example.json",
    ".github/workflows/publish.yml",
    "Makefile",
    "requirements-dev.txt",
    "CLAUDE.md",
    "AGENTS.md",
)
KEPT = (
    "__init__.py",
    "pyproject.toml",
    "requirements.txt",
    "LICENSE",
    "README.md",
    "CHANGELOG.md",
    "kikotools/tools/model_downloader/node.py",
    "web/kiko_local_image_loader.js",
)


def patterns():
    lines = (ROOT / ".comfyignore").read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and line[0] != "#"]


def ignored(path):
    """The rules this file allows: ``/folder/`` or a root file, both from the root."""
    for pattern in patterns():
        if pattern.endswith("/"):
            if path.startswith(pattern.lstrip("/")):
                return True
        elif fnmatch.fnmatchcase(path, pattern.lstrip("/")):
            return True
    return False


def test_every_rule_is_anchored_to_the_root():
    # Unanchored, "tools/" also drops kikotools/tools/ and "tests/" any nested tests/.
    for pattern in patterns():
        assert pattern.startswith("/"), pattern
        assert "!" not in pattern, pattern


@pytest.mark.parametrize("path", DEVELOPMENT)
def test_development_files_are_left_out(path):
    assert ignored(path)


@pytest.mark.parametrize("path", KEPT)
def test_package_files_stay(path):
    assert not ignored(path)


def test_runtime_folders_ship_whole():
    for folder in RUNTIME_DIRS:
        for file in (ROOT / folder).rglob("*"):
            if file.is_file() and "__pycache__" not in file.parts:
                relative = file.relative_to(ROOT).as_posix()
                assert not ignored(relative), relative


def test_registry_matcher_agrees():
    """comfy-cli matches with pathspec's gitwildmatch; check the rules with it too."""
    pathspec = pytest.importorskip("pathspec")
    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns())
    for folder in RUNTIME_DIRS:
        for file in (ROOT / folder).rglob("*.py"):
            assert not spec.match_file(file.relative_to(ROOT).as_posix()), file
    for path in DEVELOPMENT:
        assert spec.match_file(path), path


def test_runtime_code_imports_nothing_left_out():
    sources = [ROOT / "__init__.py", *(ROOT / "kikotools").rglob("*.py")]
    for source in sources:
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                names = [node.module or ""]
            for name in names:
                assert name.split(".")[0] not in (
                    "tests",
                    "scripts",
                    "tools",
                    "examples",
                ), source
