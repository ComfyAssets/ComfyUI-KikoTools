from kikotools.tools.model_resolution_picker.logic import (
    MEGAPIXEL,
    generate_size,
    ratio_label,
    round_to_step,
)


def test_round_to_step_rounds_nearest_and_never_below_minimum():
    assert round_to_step(1000, 32) == 992
    assert round_to_step(1232, 16) == 1232
    assert round_to_step(70, 32) == 64
    assert round_to_step(10, 64) == 64
    assert round_to_step(1016, 64) == 1024


def test_generate_size_matches_core_resolution_selector():
    assert generate_size(1, 1, 1.0, 8) == (1024, 1024)
    assert generate_size(16, 9, 2.0, 16) == (1936, 1088)
    assert generate_size(3, 2, 4.0, 32) == (2496, 1664)
    assert generate_size(21, 9, 0.25, 64) == (768, 320)


def test_ratio_label_reduces_and_aliases():
    assert ratio_label(1024, 1024) == "1:1"
    assert ratio_label(1216, 832) == "19:13"
    assert ratio_label(1280, 800) == "16:10"
    assert ratio_label(1344, 576) == "21:9"
    assert MEGAPIXEL == 1024 * 1024
