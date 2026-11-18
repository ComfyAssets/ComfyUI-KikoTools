"""scripts/changelog_section.py picks the release notes for a tag."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "changelog_section.py"


def run(tag, changelog):
    return subprocess.run(
        [sys.executable, str(SCRIPT), tag, str(changelog)],
        capture_output=True,
        text=True,
    )


def test_extracts_1_6_0_from_the_real_changelog():
    result = run("v1.6.0", ROOT / "CHANGELOG.md")

    assert result.returncode == 0
    assert result.stdout.startswith("### Prompt Enhancer")
    assert "no_text_sentence" in result.stdout
    assert "## " not in result.stdout.replace("### ", "")


def test_missing_version_fails_with_message(tmp_path):
    result = run("v9.9.9", ROOT / "CHANGELOG.md")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "## 9.9.9" in result.stderr


def test_last_section_runs_to_end_of_file(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## 2.0.0\n\nNew.\n\n## 1.0.0\n\nFirst.\nSecond.\n")

    result = run("v1.0.0", changelog)

    assert result.returncode == 0
    assert result.stdout == "First.\nSecond.\n"


def test_section_stops_at_next_heading(tmp_path):
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("## 2.0.0\n\n### Added\n\nNew.\n\n## 1.0.0\n\nFirst.\n")

    result = run("v2.0.0", changelog)

    assert result.stdout == "### Added\n\nNew.\n"


def test_script_stays_out_of_registry_package():
    ignore = (ROOT / ".comfyignore").read_text().splitlines()

    assert "/scripts/" in ignore
