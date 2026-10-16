"""Ensure the documented test command actually invokes pytest and fails closed."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    os.name == "nt" or not shutil.which("make"), reason="Requires POSIX make"
)
def test_make_test_runs_pytest_and_propagates_failure(tmp_path: Path) -> None:
    recorder = tmp_path / "runner.py"
    arguments = tmp_path / "arguments.json"
    recorder.write_text(
        "import json,sys\n"
        f"with open({str(arguments)!r}, 'w') as output:\n"
        "    json.dump(sys.argv[1:], output)\n"
        "sys.exit(7)\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-o",
            "venv",
            "test",
            f"PYTHON_CMD={shlex.join([sys.executable, str(recorder)])}",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert json.loads(arguments.read_text()) == ["-m", "pytest", "tests"]
    assert result.returncode != 0
