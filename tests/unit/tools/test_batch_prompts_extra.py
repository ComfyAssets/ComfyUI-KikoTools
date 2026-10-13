"""Additional behavioural tests for batch_prompts (logic, state manager, node)."""

import json
import re

import pytest

from kikotools.tools.batch_prompts import logic
from kikotools.tools.batch_prompts import node as node_mod
from kikotools.tools.batch_prompts.node import BatchPromptsNode
from kikotools.tools.batch_prompts.state_manager import StateManager


@pytest.fixture
def prompt_file(tmp_path):
    f = tmp_path / "prompts.txt"
    f.write_text("alpha\n---\nbeta Negative: ugly\n---\n\n---\ngamma\nline two\n")
    return str(f)


@pytest.fixture
def state(tmp_path, monkeypatch):
    """Isolated StateManager injected in place of the global one."""
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    sm = StateManager()
    monkeypatch.setattr(node_mod, "STATE_MANAGER", sm)
    monkeypatch.setattr(BatchPromptsNode, "_prompt_cache", {})
    return sm


class TestStateManager:
    def test_creates_state_dir_under_tempdir(self, state, tmp_path):
        assert state.state_dir.parent == tmp_path
        assert state.state_dir.is_dir()

    def test_empty_state_when_no_file(self, state):
        assert state.get_state() == {}
        assert state.get_execution_count("x") == 0

    def test_increment_returns_previous_count(self, state):
        assert state.increment_execution_count("f") == 0
        assert state.increment_execution_count("f") == 1
        assert state.get_execution_count("f") == 2

    def test_counts_are_per_file(self, state):
        state.increment_execution_count("a")
        assert state.get_execution_count("b") == 0

    def test_reset(self, state):
        state.increment_execution_count("a")
        state.reset_execution_count("a")
        assert state.get_execution_count("a") == 0

    def test_corrupt_state_file_is_treated_as_empty(self, state):
        state.state_file.write_text("{oops")
        assert state.get_state() == {}
        assert state.increment_execution_count("a") == 0

    def test_state_persists_across_instances(self, state):
        state.increment_execution_count("a")
        assert StateManager().get_execution_count("a") == 1

    def test_save_failure_is_swallowed(self, state, capsys):
        state.state_file = state.state_dir  # a directory: open() fails
        state.save_state({"a": 1})
        assert "Failed to save state" in capsys.readouterr().out


class TestLogic:
    def test_load_prompts_splits_and_skips_empty(self, prompt_file):
        assert logic.load_prompts_from_file(prompt_file) == [
            "alpha",
            "beta Negative: ugly",
            "gamma\nline two",
        ]

    def test_load_missing_file_returns_empty(self, tmp_path):
        assert logic.load_prompts_from_file(str(tmp_path / "nope.txt")) == []

    def test_get_prompt_at_index(self):
        p = ["a", "b", "c"]
        assert logic.get_prompt_at_index(p, 4) == ("b", 1)
        assert logic.get_prompt_at_index(p, 4, wrap=False) == ("c", 2)
        assert logic.get_prompt_at_index([], 3) == ("", 0)

    def test_get_next_prompt(self):
        p = ["a", "b", "c"]
        assert logic.get_next_prompt(p, 2) == ("a", 0)
        assert logic.get_next_prompt(p, 2, wrap=False) == ("c", 2)
        assert logic.get_next_prompt(p, 0) == ("b", 1)
        assert logic.get_next_prompt([], 0) == ("", 0)

    def test_preview(self):
        assert logic.get_prompt_preview("short", 10) == "short"
        assert logic.get_prompt_preview("x" * 20, 10) == "x" * 10 + "..."

    def test_parse_file_list(self):
        assert logic.parse_prompt_file_list(" a.txt, ,b.txt ,") == ["a.txt", "b.txt"]
        assert logic.parse_prompt_file_list("") == []

    def test_merge_multiple_files(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("1---2")
        b.write_text("3")
        assert logic.merge_prompts_from_multiple_files([str(a), str(b)]) == [
            "1",
            "2",
            "3",
        ]

    def test_batch_info(self):
        info = logic.get_batch_info(["a", "b", "c", "d"], 1)
        assert info["progress"] == "2/4"
        assert info["percentage"] == 25
        assert info["remaining"] == 2
        assert info["is_complete"] is False
        assert logic.get_batch_info(["a"], 0)["is_complete"] is True

    def test_batch_info_empty(self):
        info = logic.get_batch_info([], 0)
        assert info["progress"] == "0/0" and info["is_complete"] is True
        assert info["percentage"] == 0 and info["remaining"] == 0

    def test_validate_prompt_file(self, tmp_path, prompt_file):
        assert logic.validate_prompt_file(prompt_file) == (True, "")
        assert logic.validate_prompt_file("") == (False, "No file path provided")
        ok, msg = logic.validate_prompt_file(str(tmp_path / "missing"))
        assert not ok and "not found" in msg
        ok, msg = logic.validate_prompt_file(str(tmp_path))
        assert not ok and "not a file" in msg

    def test_validate_unreadable_file(self, tmp_path):
        f = tmp_path / "bin.txt"
        f.write_bytes(b"\xff\xfe\xfa")
        ok, msg = logic.validate_prompt_file(str(f))
        assert not ok and "Cannot read file" in msg

    def test_format_for_display(self):
        assert logic.format_prompt_for_display("hi", 0, 3) == (
            "[Prompt 1/3]\n------------\nhi"
        )

    def test_split_positive_negative(self):
        assert logic.split_prompt_into_positive_negative("cat NEGATIVE: dog") == (
            "cat",
            "dog",
        )
        assert logic.split_prompt_into_positive_negative("cat") == ("cat", "")
        assert logic.split_prompt_into_positive_negative("a || b", "||") == ("a", "b")

    def test_batch_queue(self):
        assert logic.create_batch_queue([]) == []
        assert logic.create_batch_queue(list("abcde"), 2) == [[0, 1], [2, 3], [4]]

    def test_batch_queue_randomized_is_permutation(self):
        flat = [i for b in logic.create_batch_queue(list("abcdef"), 4, True) for i in b]
        assert sorted(flat) == list(range(6))


class TestNode:
    def run(self, node, prompt_file, **kw):
        args = dict(
            prompt_file=prompt_file,
            index=0,
            auto_increment=False,
            wrap_around=True,
            split_negative=True,
            show_preview=True,
        )
        args.update(kw)
        return node.process_batch_prompts(**args)

    def test_input_types_shape(self):
        spec = BatchPromptsNode.INPUT_TYPES()
        assert set(spec["required"]) == {
            "prompt_file",
            "index",
            "auto_increment",
            "wrap_around",
            "split_negative",
        }
        assert len(BatchPromptsNode.RETURN_TYPES) == len(BatchPromptsNode.RETURN_NAMES)

    def test_manual_index_with_negative_split(self, state, prompt_file):
        out = self.run(BatchPromptsNode(), prompt_file, index=1)
        pos, neg, full, nxt, idx, total, info = out
        assert (pos, neg) == ("beta", "ugly")
        assert full == "beta Negative: ugly"
        assert nxt == "gamma\nline two"
        assert (idx, total) == (1, 3)
        assert info == "Prompt 2 of 3 (33.3% complete)"

    def test_no_split(self, state, prompt_file):
        out = self.run(BatchPromptsNode(), prompt_file, index=1, split_negative=False)
        assert out[0] == "beta Negative: ugly" and out[1] == ""

    def test_wrap_vs_clamp(self, state, prompt_file):
        node = BatchPromptsNode()
        assert self.run(node, prompt_file, index=4)[4] == 1
        assert self.run(node, prompt_file, index=4, wrap_around=False)[4] == 2

    def test_auto_increment_walks_through_prompts(self, state, prompt_file):
        node = BatchPromptsNode()
        seen = [
            self.run(node, prompt_file, auto_increment=True, index=99)[4]
            for _ in range(4)
        ]
        assert seen == [0, 1, 2, 0]

    def test_reload_file_resets_counter_and_rereads(self, state, prompt_file):
        node = BatchPromptsNode()
        self.run(node, prompt_file, auto_increment=True)
        self.run(node, prompt_file, auto_increment=True)
        with open(prompt_file, "w") as f:
            f.write("only one")
        # cached content is stale until reload_file is requested
        assert self.run(node, prompt_file, index=0)[5] == 3
        out = self.run(node, prompt_file, index=0, reload_file=True)
        assert out[5] == 1 and out[2] == "only one"
        assert state.get_execution_count(prompt_file) == 0

    def test_relative_path_resolved_against_input_dir(
        self, state, tmp_path, monkeypatch
    ):
        (tmp_path / "rel.txt").write_text("x---y")
        import sys

        monkeypatch.setattr(
            sys.modules["folder_paths"],
            "get_input_directory",
            lambda: str(tmp_path),
            raising=False,
        )
        out = self.run(BatchPromptsNode(), "rel.txt", index=1)
        assert out[2] == "y"

    def test_relative_path_falls_back_to_cwd(self, state, tmp_path, monkeypatch):
        import sys

        def boom():
            raise RuntimeError("no input dir")

        monkeypatch.setattr(
            sys.modules["folder_paths"], "get_input_directory", boom, raising=False
        )
        monkeypatch.chdir(tmp_path)
        (tmp_path / "cwd.txt").write_text("only")
        assert self.run(BatchPromptsNode(), "cwd.txt")[2] == "only"

    def test_missing_file_raises(self, state, tmp_path):
        with pytest.raises(ValueError, match="Invalid prompt file"):
            self.run(BatchPromptsNode(), str(tmp_path / "missing.txt"))

    def test_empty_file_raises(self, state, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("---\n---")
        with pytest.raises(ValueError, match="No prompts found"):
            self.run(BatchPromptsNode(), str(f))

    def test_is_changed_always_differs(self):
        import time

        a = BatchPromptsNode.IS_CHANGED()
        time.sleep(0.002)
        b = BatchPromptsNode.IS_CHANGED()
        assert a != b and re.fullmatch(r"[\d.]+", a)
