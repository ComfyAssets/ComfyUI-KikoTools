"""Path-security tests for the Local Image Loader (logic helpers)."""

import os

import pytest

from kikotools.tools.local_image_loader.logic import (
    is_allowed_image_path,
    is_within_roots,
    list_subdirectories,
    resolve_path,
)


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "a.png").write_bytes(b"x")
    (root / "notes.txt").write_text("x")
    (root / "sub").mkdir()
    (root / "sub" / "b.JPG").write_bytes(b"x")
    sibling = tmp_path / "root_evil"  # shares a string prefix with root
    sibling.mkdir()
    (sibling / "c.png").write_bytes(b"x")
    return tmp_path


class TestResolvePath:
    @pytest.mark.parametrize("bad", [None, "", 5, "a\0b", b"bytes"])
    def test_invalid_input_returns_none(self, bad):
        assert resolve_path(bad) is None

    def test_resolves_dotdot_and_symlinks(self, tree):
        link = tree / "link"
        link.symlink_to(tree / "root")
        got = resolve_path(str(link / "sub" / ".." / "a.png"))
        assert got == os.path.realpath(tree / "root" / "a.png")


class TestIsWithinRoots:
    def test_inside_root(self, tree):
        assert is_within_roots(str(tree / "root" / "sub"), [str(tree / "root")])

    def test_root_itself_allowed(self, tree):
        assert is_within_roots(str(tree / "root"), [str(tree / "root")])

    def test_prefix_sibling_rejected(self, tree):
        assert not is_within_roots(
            str(tree / "root_evil" / "c.png"), [str(tree / "root")]
        )

    def test_dotdot_escape_rejected(self, tree):
        escape = str(tree / "root" / ".." / "root_evil" / "c.png")
        assert not is_within_roots(escape, [str(tree / "root")])

    def test_symlink_escape_rejected(self, tree):
        (tree / "root" / "out").symlink_to(tree / "root_evil")
        assert not is_within_roots(
            str(tree / "root" / "out" / "c.png"), [str(tree / "root")]
        )

    def test_empty_or_invalid_roots_ignored(self, tree):
        assert not is_within_roots(str(tree), [])
        assert not is_within_roots(str(tree), [None, "", 3, "a\0b"])

    def test_invalid_path(self):
        assert not is_within_roots(None, ["/"])


class TestIsAllowedImagePath:
    def test_image_in_root(self, tree):
        roots = [str(tree / "root")]
        assert is_allowed_image_path(str(tree / "root" / "a.png"), roots)
        assert is_allowed_image_path(str(tree / "root" / "sub" / "b.JPG"), roots)

    def test_non_image_in_root_rejected(self, tree):
        assert not is_allowed_image_path(
            str(tree / "root" / "notes.txt"), [str(tree / "root")]
        )

    def test_image_outside_root_rejected(self, tree):
        assert not is_allowed_image_path(
            str(tree / "root_evil" / "c.png"), [str(tree / "root")]
        )

    def test_root_set_to_filesystem_root_still_requires_image_ext(self):
        assert not is_allowed_image_path("/etc/passwd", ["/"])

    def test_symlink_with_image_name_to_secret_rejected(self, tree):
        secret = tree / "root_evil" / "id_rsa"
        secret.write_text("secret")
        (tree / "root" / "fake.png").symlink_to(secret)
        assert not is_allowed_image_path(
            str(tree / "root" / "fake.png"), [str(tree / "root"), str(tree)]
        )

    def test_invalid_path(self):
        assert not is_allowed_image_path(None, ["/"])


class TestListSubdirectories:
    def test_trailing_sep_lists_children_dirs_only(self, tree):
        got = list_subdirectories(str(tree / "root") + os.sep)
        assert got == [os.path.join(str(tree / "root") + os.sep, "sub")]

    def test_prefix_match_in_parent(self, tree):
        got = list_subdirectories(str(tree / "ro"))
        assert got == [str(tree / "root"), str(tree / "root_evil")]

    def test_missing_dir_returns_empty(self, tree):
        assert list_subdirectories(str(tree / "nope") + os.sep) == []
        assert list_subdirectories(str(tree / "nope" / "x")) == []

    def test_limit(self, tree):
        for i in range(5):
            (tree / f"d{i}").mkdir()
        assert len(list_subdirectories(str(tree) + os.sep, limit=3)) == 3

    def test_relative_without_parent_returns_empty(self):
        assert list_subdirectories("zzz_not_here") == []

    def test_top_level_prefix(self):
        got = list_subdirectories("/e")
        assert all(os.path.isdir(p) for p in got)
        assert all(p.startswith("/e") for p in got)
