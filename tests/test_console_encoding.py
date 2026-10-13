"""Loading the node must not depend on the console being able to print emoji.

A Windows console using a legacy code page (cp1252, or cp437 in a plain
cmd window) raises UnicodeEncodeError on characters like the emoji in our
display names. At import time that aborts loading the whole node pack.
"""

import contextlib
import importlib.util
import io
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def strict_console(encoding):
    return io.TextIOWrapper(io.BytesIO(), encoding=encoding, errors="strict")


@pytest.mark.parametrize("encoding", ["cp1252", "cp437"])
def test_package_loads_with_a_legacy_windows_console(encoding):
    name = f"kikotools_pkg_{encoding}"
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(ROOT, "__init__.py"), submodule_search_locations=[ROOT]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    stream = strict_console(encoding)
    try:
        with contextlib.redirect_stdout(stream):
            spec.loader.exec_module(module)
    finally:
        for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
            sys.modules.pop(key)

    stream.flush()
    banner = stream.buffer.getvalue().decode(encoding)
    assert "Loaded:" in banner
    assert "Model Downloader" in banner  # display name kept, emoji dropped


def test_preset_validation_messages_are_ascii(monkeypatch):
    from kikotools.tools.width_height_selector import presets

    bad = presets.PRESET_METADATA[next(iter(presets.PRESET_METADATA))]
    bad = bad._replace(width=1001)  # not divisible by 8
    monkeypatch.setattr(presets, "PRESET_METADATA", {"bad 1001×1024": bad})
    stream = strict_console("cp437")
    with contextlib.redirect_stdout(stream):
        assert presets.validate_preset_dimensions() is False
