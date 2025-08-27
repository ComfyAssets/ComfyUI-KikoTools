"""Unit tests for Batch Prompts node."""

import pytest
import tempfile
import os
from pathlib import Path
from kikotools.tools.batch_prompts.logic import (
    load_prompts_from_file,
    get_prompt_at_index,
    get_next_prompt,
    get_prompt_preview,
    get_batch_info,
    validate_prompt_file,
    format_prompt_for_display,
    split_prompt_into_positive_negative,
    create_batch_queue,
)
from kikotools.tools.batch_prompts.node import BatchPromptsNode


class TestBatchPromptsLogic:
    """Test batch prompts logic functions."""

    def test_load_prompts_from_file(self, tmp_path):
        """Test loading prompts from a file with --- separators."""
        # Create test file
        test_file = tmp_path / "test_prompts.txt"
        test_content = """First prompt here
with multiple lines
---
Second prompt
also multiline
---
Third prompt"""
        test_file.write_text(test_content)

        # Load prompts
        prompts = load_prompts_from_file(str(test_file))

        assert len(prompts) == 3
        assert "First prompt here\nwith multiple lines" in prompts[0]
        assert "Second prompt\nalso multiline" in prompts[1]
        assert "Third prompt" in prompts[2]

    def test_load_prompts_empty_sections(self, tmp_path):
        """Test loading prompts with empty sections."""
        test_file = tmp_path / "test_prompts.txt"
        test_content = """First prompt
---

---
Second prompt
---
"""
        test_file.write_text(test_content)

        prompts = load_prompts_from_file(str(test_file))

        # Should only get non-empty prompts
        assert len(prompts) == 2
        assert "First prompt" in prompts[0]
        assert "Second prompt" in prompts[1]

    def test_get_prompt_at_index(self):
        """Test getting prompt at specific index."""
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]

        # Normal access
        prompt, idx = get_prompt_at_index(prompts, 1, wrap=False)
        assert prompt == "Prompt 2"
        assert idx == 1

        # With wrapping
        prompt, idx = get_prompt_at_index(prompts, 4, wrap=True)
        assert prompt == "Prompt 2"  # 4 % 3 = 1
        assert idx == 1

        # Without wrapping, clamp to last
        prompt, idx = get_prompt_at_index(prompts, 5, wrap=False)
        assert prompt == "Prompt 3"
        assert idx == 2

    def test_get_next_prompt(self):
        """Test getting next prompt in sequence."""
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]

        # Normal next
        prompt, idx = get_next_prompt(prompts, 0, wrap=True)
        assert prompt == "Prompt 2"
        assert idx == 1

        # Wrap around
        prompt, idx = get_next_prompt(prompts, 2, wrap=True)
        assert prompt == "Prompt 1"
        assert idx == 0

        # No wrap
        prompt, idx = get_next_prompt(prompts, 2, wrap=False)
        assert prompt == "Prompt 3"
        assert idx == 2

    def test_get_prompt_preview(self):
        """Test prompt preview truncation."""
        short_prompt = "Short prompt"
        long_prompt = "This is a very long prompt " * 10

        # Short prompt unchanged
        preview = get_prompt_preview(short_prompt, 100)
        assert preview == short_prompt

        # Long prompt truncated
        preview = get_prompt_preview(long_prompt, 50)
        assert len(preview) == 53  # 50 + "..."
        assert preview.endswith("...")

    def test_split_prompt_positive_negative(self):
        """Test splitting prompts into positive and negative."""
        # With negative
        prompt = "Beautiful landscape\nNegative: blurry, dark"
        pos, neg = split_prompt_into_positive_negative(prompt)
        assert pos == "Beautiful landscape"
        assert neg == "blurry, dark"

        # Without negative
        prompt = "Just a positive prompt"
        pos, neg = split_prompt_into_positive_negative(prompt)
        assert pos == "Just a positive prompt"
        assert neg == ""

        # Case insensitive
        prompt = "Positive part\nnegative: negative part"
        pos, neg = split_prompt_into_positive_negative(prompt)
        assert pos == "Positive part"
        assert neg == "negative part"

    def test_get_batch_info(self):
        """Test batch information generation."""
        prompts = ["P1", "P2", "P3", "P4", "P5"]

        info = get_batch_info(prompts, 2)
        assert info["current_index"] == 2
        assert info["total_prompts"] == 5
        assert info["progress"] == "3/5"
        assert info["percentage"] == 40.0
        assert info["remaining"] == 2
        assert info["is_complete"] == False

        # Last prompt
        info = get_batch_info(prompts, 4)
        assert info["is_complete"] == True
        assert info["remaining"] == 0

    def test_validate_prompt_file(self, tmp_path):
        """Test prompt file validation."""
        # Valid file
        valid_file = tmp_path / "valid.txt"
        valid_file.write_text("content")
        is_valid, error = validate_prompt_file(str(valid_file))
        assert is_valid
        assert error == ""

        # Non-existent file
        is_valid, error = validate_prompt_file("/nonexistent/file.txt")
        assert not is_valid
        assert "not found" in error

        # Empty path
        is_valid, error = validate_prompt_file("")
        assert not is_valid
        assert "No file path" in error

    def test_format_prompt_for_display(self):
        """Test prompt display formatting."""
        prompt = "Test prompt"
        formatted = format_prompt_for_display(prompt, 2, 5)

        assert "[Prompt 3/5]" in formatted
        assert "Test prompt" in formatted
        assert "---" in formatted

    def test_create_batch_queue(self):
        """Test batch queue creation."""
        prompts = ["P1", "P2", "P3", "P4", "P5"]

        # Batch size 2
        batches = create_batch_queue(prompts, batch_size=2, randomize=False)
        assert len(batches) == 3
        assert batches[0] == [0, 1]
        assert batches[1] == [2, 3]
        assert batches[2] == [4]

        # Batch size 1
        batches = create_batch_queue(prompts, batch_size=1, randomize=False)
        assert len(batches) == 5
        assert all(len(b) == 1 for b in batches)


class TestBatchPromptsNode:
    """Test BatchPromptsNode class."""

    def test_node_input_types(self):
        """Test node input type definitions."""
        input_types = BatchPromptsNode.INPUT_TYPES()

        assert "required" in input_types
        assert "prompt_file" in input_types["required"]
        assert "index" in input_types["required"]
        assert "auto_increment" in input_types["required"]
        assert "wrap_around" in input_types["required"]
        assert "split_negative" in input_types["required"]

        assert "optional" in input_types
        assert "reload_file" in input_types["optional"]
        assert "show_preview" in input_types["optional"]

    def test_node_return_types(self):
        """Test node return type definitions."""
        assert BatchPromptsNode.RETURN_TYPES == (
            "STRING",
            "STRING",
            "STRING",
            "STRING",
            "INT",
            "INT",
            "STRING",
        )
        assert BatchPromptsNode.RETURN_NAMES == (
            "positive",
            "negative",
            "full_prompt",
            "next_prompt",
            "current_index",
            "total_prompts",
            "batch_info",
        )
        assert BatchPromptsNode.FUNCTION == "process_batch_prompts"
        assert "ComfyAssets" in BatchPromptsNode.CATEGORY

    def test_process_batch_prompts(self, tmp_path):
        """Test processing batch prompts."""
        # Create test file
        test_file = tmp_path / "test_prompts.txt"
        test_content = """Beautiful sunset
Negative: dark, blurry
---
Mountain landscape
Negative: fog, rain
---
Ocean view"""
        test_file.write_text(test_content)

        node = BatchPromptsNode()

        # Process first prompt
        result = node.process_batch_prompts(
            prompt_file=str(test_file),
            index=0,
            auto_increment=False,
            wrap_around=True,
            split_negative=True,
            reload_file=False,
            show_preview=False,
        )

        positive, negative, full, next_prompt, idx, total, info = result

        assert positive == "Beautiful sunset"
        assert negative == "dark, blurry"
        assert "Beautiful sunset" in full
        assert "Mountain landscape" in next_prompt
        assert idx == 0
        assert total == 3
        assert "1 of 3" in info

    def test_process_without_negative_split(self, tmp_path):
        """Test processing without splitting negative prompts."""
        test_file = tmp_path / "test_prompts.txt"
        test_content = """Full prompt with Negative: included"""
        test_file.write_text(test_content)

        node = BatchPromptsNode()

        result = node.process_batch_prompts(
            prompt_file=str(test_file),
            index=0,
            auto_increment=False,
            wrap_around=True,
            split_negative=False,
            reload_file=False,
            show_preview=False,
        )

        positive, negative, full, _, _, _, _ = result

        assert positive == "Full prompt with Negative: included"
        assert negative == ""

    def test_wrap_around_behavior(self, tmp_path):
        """Test wrap around behavior."""
        test_file = tmp_path / "test_prompts.txt"
        test_content = """Prompt 1
---
Prompt 2"""
        test_file.write_text(test_content)

        node = BatchPromptsNode()

        # Test with wrap
        result = node.process_batch_prompts(
            prompt_file=str(test_file),
            index=2,  # Beyond end
            auto_increment=False,
            wrap_around=True,
            split_negative=False,
            reload_file=False,
            show_preview=False,
        )

        positive, _, _, _, idx, _, _ = result
        assert positive == "Prompt 1"  # Wrapped to index 0
        assert idx == 0

        # Test without wrap
        result = node.process_batch_prompts(
            prompt_file=str(test_file),
            index=2,  # Beyond end
            auto_increment=False,
            wrap_around=False,
            split_negative=False,
            reload_file=True,  # Force reload
            show_preview=False,
        )

        positive, _, _, _, idx, _, _ = result
        assert positive == "Prompt 2"  # Clamped to last
        assert idx == 1
