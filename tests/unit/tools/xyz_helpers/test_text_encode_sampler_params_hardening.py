"""Hardening tests for Text Encode Sampler Params."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from kikotools.tools.xyz_helpers.text_encode_sampler_params import (
    TextEncodeSamplerParamsNode,
)
from kikotools.tools.xyz_helpers.text_encode_sampler_params.logic import (
    encode_prompts,
    split_prompts,
)


class TestSplitPrompts:
    def test_trailing_separator_without_newline(self):
        assert split_prompts("a\n---") == ["a"]

    def test_leading_separator(self):
        assert split_prompts("---\na\n---\nb") == ["a", "b"]

    def test_separator_mid_line_does_not_split(self):
        assert split_prompts("x, ----\ny") == ["x, ----\ny"]

    def test_inline_dashes_do_not_split(self):
        assert split_prompts("a --- b") == ["a --- b"]

    def test_surrounding_spaces_allowed(self):
        assert split_prompts("a\n  ---  \nb") == ["a", "b"]

    def test_windows_line_endings(self):
        assert split_prompts("a\r\n---\r\nb") == ["a", "b"]

    def test_mixed_chars_are_not_a_separator(self):
        assert split_prompts("a\n-*-\nb") == ["a\n-*-\nb"]

    def test_all_separator_types(self):
        assert split_prompts("a\n***\nb\n===\nc\n~~~\nd") == ["a", "b", "c", "d"]

    def test_only_separators_yields_no_prompts(self):
        assert split_prompts("---\n---") == []

    def test_empty(self):
        assert split_prompts("") == []


def _nodes_module(encode):
    mod = MagicMock()
    mod.CLIPTextEncode.return_value.encode = encode
    return patch.dict(sys.modules, {"nodes": mod})


class TestEncodePrompts:
    def test_alignment_preserved(self):
        with _nodes_module(lambda clip, text: (f"enc:{text}",)):
            assert encode_prompts(["a", "b"], object()) == ["enc:a", "enc:b"]

    def test_failure_raises_with_index(self):
        def encode(clip, text):
            if text == "b":
                raise RuntimeError("boom")
            return (f"enc:{text}",)

        with _nodes_module(encode):
            with pytest.raises(ValueError, match="prompt 2"):
                encode_prompts(["a", "b", "c"], object())

    def test_none_result_raises(self):
        with _nodes_module(lambda clip, text: (None,)):
            with pytest.raises(ValueError, match="prompt 1"):
                encode_prompts(["a"], object())


class TestNode:
    def test_node_raises_when_encoding_fails(self):
        def encode(clip, text):
            raise RuntimeError("boom")

        with _nodes_module(encode):
            with pytest.raises(ValueError, match="prompt 1"):
                TextEncodeSamplerParamsNode().encode_prompts("a\n---\nb", object())

    def test_node_success_keeps_text_and_encoded_aligned(self):
        with _nodes_module(lambda clip, text: (f"enc:{text}",)):
            (cond,) = TextEncodeSamplerParamsNode().encode_prompts(
                "a\n---\nb", object()
            )
        assert cond["text"] == ["a", "b"]
        assert cond["encoded"] == ["enc:a", "enc:b"]

    def test_invalid_text_raises(self):
        with pytest.raises(ValueError):
            TextEncodeSamplerParamsNode().encode_prompts("   ", object())

    def test_only_separators_returns_empty_conditioning(self):
        (cond,) = TextEncodeSamplerParamsNode().encode_prompts("---\n---", object())
        assert cond == {"text": [], "encoded": []}
