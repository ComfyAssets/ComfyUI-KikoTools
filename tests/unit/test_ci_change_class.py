"""CI runs tests only for changes that can affect code (#118).

``tools/ci/change_class.py`` sorts a change by the files it touches: ``inert``
(no test and no shipped code reads the file) or ``code`` (everything else, and
every case of doubt).
"""

import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "ci"))
import change_class  # noqa: E402

SCRIPT = ROOT / "tools" / "ci" / "change_class.py"


def _isolated_environment(**extra):
    """The environment without git's own variables and the script's inputs.

    A git hook exports ``GIT_DIR`` and ``GIT_INDEX_FILE`` for the repository
    being pushed. A child ``git`` that inherits them works on that repository
    instead of the temp one, so the pre-push hook must never pass them on.
    """
    kept = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_") and key not in change_class.ENVIRONMENT
    }
    return {**kept, **extra}


class TestClassify(unittest.TestCase):
    def test_files_nothing_reads_are_inert(self):
        for paths in (
            ["README.md"],
            ["CHANGELOG.md", "TESTING.md", "CLAUDE.md", "AGENTS.md"],
            [".github/FUNDING.yml", ".github/pull_request_template.md"],
            ["docs/screenshots/seed-history/dark.png", "docs/ui-migration.md"],
            ["examples/documentation/a.md", ".github/ISSUE_TEMPLATE/bug_report.md"],
        ):
            self.assertEqual(change_class.classify(paths), "inert", paths)

    def test_anything_else_is_code(self):
        for paths in (
            ["kikotools/tools/seed_history/node.py"],
            ["README.md", "web/js/kiko_seed_history.js"],
            [".github/FUNDING.yml", "pyproject.toml"],
            # Shipped to users as release assets.
            ["examples/workflows/display_text_example.json"],
            [".github/workflows/tests.yml"],
            [".comfyignore"],
            ["LICENSE"],
            # Look-alikes of listed names are not listed.
            ["kikotools/README.md"],
            ["web/docs/x.png"],
            ["README.md.py"],
            [".github/funding.yml"],
        ):
            self.assertEqual(change_class.classify(paths), "code", paths)

    def test_no_files_is_code(self):
        self.assertEqual(change_class.classify([]), "code")

    def test_no_listed_folder_holds_code(self):
        suffixes = {".py", ".js", ".mjs", ".ts", ".css", ".html", ".yml", ".yaml"}
        for folder in change_class.INERT_FOLDERS:
            for file in (ROOT / folder).rglob("*"):
                self.assertNotIn(file.suffix, suffixes, file)


class TestCommandLine(unittest.TestCase):
    """The script against a real repository with one commit per kind of change."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        # As in a git hook: these name another repository, which must stay untouched.
        self.other = Path(self.tmp.name) / "other.git"
        patcher = unittest.mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": str(self.other),
                "GIT_INDEX_FILE": str(self.other / "index"),
                "GIT_WORK_TREE": str(self.tmp.name),
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(lambda: self.assertFalse(self.other.exists()))
        self.git("init", "-q", "-b", "main")
        self.commit({"py/a.py": "a\n", "LICENSE": "r\n"})
        self.base = self.head()

    def git(self, *args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.repo,
            env=_isolated_environment(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, files):
        for name, text in files.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "change")

    def head(self):
        return self.git("rev-parse", "HEAD")

    def run_script(self, *args, **env):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.repo,
            env=_isolated_environment(**env),
            capture_output=True,
            text=True,
        )

    def class_of(self, **env):
        result = self.run_script(**env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_a_pull_request_is_classed_by_its_own_files(self):
        self.git("checkout", "-q", "-b", "topic")
        self.commit({".github/FUNDING.yml": "x\n"})
        topic = self.head()
        # main moved on with code meanwhile: that is not this pull request's change.
        self.git("checkout", "-q", "main")
        self.commit({"py/a.py": "b\n"})
        self.assertEqual(
            self.class_of(
                EVENT_NAME="pull_request", BASE_SHA=self.head(), HEAD_SHA=topic
            ),
            "class=inert",
        )

    def test_a_push_is_classed_by_its_range(self):
        self.commit({"README.md": "r2\n", "docs/a.png": "p\n"})
        self.assertEqual(
            self.class_of(EVENT_NAME="push", BASE_SHA=self.base, HEAD_SHA=self.head()),
            "class=inert",
        )
        self.commit({"py/a.py": "c\n"})
        self.assertEqual(
            self.class_of(EVENT_NAME="push", BASE_SHA=self.base, HEAD_SHA=self.head()),
            "class=code",
        )

    def test_a_deleted_or_renamed_file_counts_under_both_names(self):
        self.git("mv", "py/a.py", "SECURITY.md")
        self.git("commit", "-q", "-m", "rename")
        self.assertEqual(
            self.class_of(EVENT_NAME="push", BASE_SHA=self.base, HEAD_SHA=self.head()),
            "class=code",
        )

    def test_doubt_is_code(self):
        self.commit({".github/FUNDING.yml": "x\n"})
        head = self.head()
        zero = "0" * 40
        for env in (
            {"EVENT_NAME": "workflow_dispatch", "BASE_SHA": self.base},
            {"EVENT_NAME": "schedule", "BASE_SHA": self.base, "HEAD_SHA": head},
            {"EVENT_NAME": "merge_group", "BASE_SHA": self.base, "HEAD_SHA": head},
            {"EVENT_NAME": "push", "BASE_SHA": zero, "HEAD_SHA": head},
            {"EVENT_NAME": "push", "BASE_SHA": "", "HEAD_SHA": head},
            {"EVENT_NAME": "push", "BASE_SHA": "f" * 40, "HEAD_SHA": head},
            {"EVENT_NAME": "push", "BASE_SHA": head, "HEAD_SHA": head},
            {},
        ):
            self.assertEqual(self.class_of(**env), "class=code", env)

    def test_the_pre_push_command_is_skipped_only_for_an_inert_push(self):
        marker = self.repo / "ran"
        command = (
            "--unless-inert",
            sys.executable,
            "-c",
            "open('ran', 'w').close()",
        )
        self.commit({".github/FUNDING.yml": "x\n"})
        refs = {"PRE_COMMIT_FROM_REF": self.base, "PRE_COMMIT_TO_REF": self.head()}
        result = self.run_script(*command, **refs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertIn("inert", result.stdout)
        # No range from pre-commit (a manual run) and a code push both run it.
        self.assertEqual(self.run_script(*command).returncode, 0)
        self.assertTrue(marker.exists())
        marker.unlink()
        self.commit({"py/a.py": "r3\n"})
        refs["PRE_COMMIT_TO_REF"] = self.head()
        self.assertEqual(self.run_script(*command, **refs).returncode, 0)
        self.assertTrue(marker.exists())

    def test_the_pre_push_command_keeps_its_exit_code(self):
        result = self.run_script(
            "--unless-inert", sys.executable, "-c", "raise SystemExit(7)"
        )
        self.assertEqual(result.returncode, 7)


if __name__ == "__main__":
    unittest.main()
