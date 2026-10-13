"""Tests for the Project File Path node."""

from datetime import date

import pytest

from kikotools.tools.project_file_path.logic import (
    build_project_path,
    sanitize_component,
    sanitize_filename,
)
from kikotools.tools.project_file_path.node import ProjectFilePathNode

TODAY = date(2026, 10, 13)


class TestSanitizeComponent:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("MyProject", "MyProject"),
            ("my project", "my_project"),
            ('a<b>c:d"e|f?g*h', "abcdefgh"),
            ("tab\there\x00", "tabhere"),
            ("  .hidden.  ", "hidden"),
            ("", ""),
        ],
    )
    def test_cleans_single_part(self, raw, expected):
        assert sanitize_component(raw) == expected

    def test_keeps_nested_folders(self):
        assert sanitize_component("renders/final") == "renders/final"
        assert sanitize_component("renders\\final") == "renders/final"

    @pytest.mark.parametrize(
        "raw", ["../../etc", "a/../../b", "..", "./.", "/abs/path", "C:\\x"]
    )
    def test_never_climbs_or_is_absolute(self, raw):
        parts = sanitize_component(raw).split("/")
        assert ".." not in parts
        assert not sanitize_component(raw).startswith("/")
        assert ":" not in sanitize_component(raw)

    def test_traversal_parts_are_dropped(self):
        assert sanitize_component("a/../../b") == "a/b"


class TestSanitizeFilename:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("image", "image"),
            ("image.png", "image"),
            ("clip.MP4", "clip"),
            ("render_v1.5", "render_v1.5"),  # not a file extension
            ("my file", "my_file"),
            ("../../evil", "evil"),
            ("a/b\\c", "abc"),
        ],
    )
    def test_cleans(self, raw, expected):
        assert sanitize_filename(raw) == expected


class TestBuildProjectPath:
    def test_basic(self):
        assert (
            build_project_path(
                "", "MyProject", "images", "image", separator="forward_slash"
            )
            == "MyProject/images/image"
        )

    def test_root_prefix(self):
        assert (
            build_project_path("work", "P", "s", "f", separator="forward_slash")
            == "work/P/s/f"
        )

    def test_empty_parts_skipped(self):
        assert build_project_path("", "P", "", "f", separator="forward_slash") == "P/f"

    def test_date_folder_between_project_and_subfolder(self):
        assert (
            build_project_path(
                "",
                "P",
                "images",
                "f",
                date_folder=True,
                separator="forward_slash",
                today=TODAY,
            )
            == "P/2026-10-13/images/f"
        )

    def test_backslash_separator_applied(self):
        assert (
            build_project_path("", "P", "a/b", "f", separator="backslash")
            == "P\\a\\b\\f"
        )

    def test_auto_uses_os_separator(self, monkeypatch):
        monkeypatch.setattr("os.sep", "\\")
        assert build_project_path("", "P", "s", "f", separator="auto") == "P\\s\\f"
        monkeypatch.setattr("os.sep", "/")
        assert build_project_path("", "P", "s", "f", separator="auto") == "P/s/f"

    def test_traversal_cannot_escape(self):
        path = build_project_path(
            "../..", "../x", "../../y", "../z", separator="forward_slash"
        )
        assert path == "x/y/z"

    @pytest.mark.parametrize("filename", ["", "   ", ".png", "///"])
    def test_empty_filename_raises(self, filename):
        with pytest.raises(ValueError, match="filename"):
            build_project_path("", "P", "s", filename)

    def test_unknown_separator_raises(self):
        with pytest.raises(ValueError, match="separator"):
            build_project_path("", "P", "s", "f", separator="pipe")


class TestNode:
    def test_input_types_match_djz_plus_date(self):
        inputs = ProjectFilePathNode.INPUT_TYPES()
        required = inputs["required"]
        assert list(required) == ["root", "project_name", "subfolder", "filename"]
        assert required["root"][1]["default"] == ""
        assert inputs["optional"]["date_folder"][1]["default"] is False
        assert inputs["optional"]["separator"][0] == [
            "auto",
            "forward_slash",
            "backslash",
        ]

    def test_metadata(self):
        assert ProjectFilePathNode.RETURN_TYPES == ("STRING",)
        assert ProjectFilePathNode.RETURN_NAMES == ("path",)
        assert ProjectFilePathNode.CATEGORY == "🫶 ComfyAssets/🛠️ Utils"

    def test_generate_path(self):
        result = ProjectFilePathNode().generate_path(
            "", "My Project", "images", "image.png", separator="forward_slash"
        )
        assert result == ("My_Project/images/image",)

    def test_generate_path_error_is_value_error(self):
        with pytest.raises(ValueError):
            ProjectFilePathNode().generate_path("", "P", "s", "")

    def test_is_changed_stable_without_date_folder(self):
        # Same inputs -> same value, so ComfyUI can cache the node
        a = ProjectFilePathNode.IS_CHANGED(date_folder=False)
        b = ProjectFilePathNode.IS_CHANGED(date_folder=False)
        assert a == b

    def test_is_changed_tracks_date(self, monkeypatch):
        from kikotools.tools.project_file_path import node as node_mod

        monkeypatch.setattr(node_mod, "_today", lambda: TODAY)
        first = ProjectFilePathNode.IS_CHANGED(date_folder=True)
        monkeypatch.setattr(node_mod, "_today", lambda: date(2026, 10, 14))
        assert ProjectFilePathNode.IS_CHANGED(date_folder=True) != first


def test_registered():
    from kikotools import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    assert NODE_CLASS_MAPPINGS["KikoProjectFilePath"] is ProjectFilePathNode
    assert NODE_DISPLAY_NAME_MAPPINGS["KikoProjectFilePath"] == "Project File Path"
