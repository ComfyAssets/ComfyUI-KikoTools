import pytest
import torch

from kikotools.tools.h3_reference_prompter.logic import (
    DEFAULT_ROLES,
    ROLES,
    SLOTS,
    clean_result,
    find_tags,
    image_key,
    item_seed,
    pair_items,
    tag_problems,
)


def test_roles_and_slots_constants():
    assert ROLES == ("character", "outfit", "pose", "other")
    assert DEFAULT_ROLES == ("character", "outfit", "pose")
    assert SLOTS == 3


def test_find_tags_reads_numbers_with_spaces_inside_brackets():
    assert find_tags("<Picture 1> and < Picture 3 >") == {1, 3}


def test_find_tags_without_tags_is_empty():
    assert find_tags("a woman in a red coat") == set()


def test_tag_problems_reports_missing_and_extra_sorted():
    draft = "<Picture 1> <Picture 2> <Picture 3>"
    result = "<Picture 1> <Picture 3> <Picture 4>"
    assert tag_problems(draft, result) == ([2], [4])


def test_tag_problems_plain_draft_and_plain_result_are_clean():
    assert tag_problems("plain draft", "plain result") == ([], [])


def test_pair_items_broadcasts_single_length_columns():
    items = pair_items(prompt=["a", "b", "c"], image_1=["img"])
    assert items == [
        {"prompt": "a", "image_1": "img"},
        {"prompt": "b", "image_1": "img"},
        {"prompt": "c", "image_1": "img"},
    ]


def test_pair_items_rejects_mismatched_lengths_naming_both():
    with pytest.raises(ValueError) as error:
        pair_items(prompt=["a", "b"], image_1=["x", "y", "z"])
    message = str(error.value)
    assert "2" in message and "3" in message


def test_pair_items_empty_column_becomes_none():
    assert pair_items(prompt=["a"], image_2=[]) == [{"prompt": "a", "image_2": None}]
    assert pair_items(prompt=["a"], image_2=[None]) == [
        {"prompt": "a", "image_2": None}
    ]


def test_item_seed_wraps_at_64_bits():
    assert item_seed(2**64 - 1, 1) == 0


def test_image_key_changes_with_content_role_model():
    base = torch.zeros(1, 4, 4, 3)
    other = torch.ones(1, 4, 4, 3)
    key = image_key(base, "character", "model-a")
    assert key == image_key(base.clone(), "character", "model-a")
    assert key != image_key(other, "character", "model-a")
    assert key != image_key(base, "outfit", "model-a")
    assert key != image_key(base, "character", "model-b")


def test_clean_result_strips_think_block():
    assert clean_result("<think>x</think>\nA woman stands.") == "A woman stands."


def test_clean_result_strips_preamble_line_and_quotes():
    assert clean_result('Here is the prompt:\n"A woman stands."') == "A woman stands."


def test_clean_result_strips_prompt_label_on_same_line():
    assert clean_result("Prompt: A woman stands.") == "A woman stands."


def test_clean_result_strips_code_fence_with_language():
    assert clean_result("```text\nA woman stands.\n```") == "A woman stands."
