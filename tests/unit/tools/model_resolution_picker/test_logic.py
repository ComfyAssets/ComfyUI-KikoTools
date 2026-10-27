from kikotools.tools.model_resolution_picker.logic import (
    MEGAPIXEL,
    generate_size,
    parse_size_label,
    ratio_label,
    round_to_step,
    size_label,
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


def test_size_label_formats_size_ratio_and_megapixels():
    assert size_label(1216, 832, "3:2") == "1216×832 - 3:2 (1.0MP)"
    assert size_label(2560, 1536, "16:9") == "2560×1536 - 16:9 (3.8MP)"


def test_size_label_uses_binary_megapixels_and_rounds_ties_up():
    assert size_label(512, 512, "1:1") == "512×512 - 1:1 (0.3MP)"
    assert size_label(1000, 1000, "1:1") == "1000×1000 - 1:1 (1.0MP)"


def test_parse_size_label_round_trips_and_rejects_garbage():
    assert parse_size_label("1216×832 - 3:2 (1.0MP)") == (1216, 832)
    assert parse_size_label(size_label(768, 1344, "9:16")) == (768, 1344)
    assert parse_size_label("custom") is None
    assert parse_size_label("garbage") is None
    assert parse_size_label("0×832 - 3:2 (1.0MP)") is None
    assert parse_size_label(None) is None
