"""Tests for Seed History tool."""

import time

from kikotools.tools.seed_history.node import SeedHistoryNode
from kikotools.tools.seed_history.logic import (
    generate_random_seed,
    validate_seed_value,
    sanitize_seed_value,
    create_history_entry,
    filter_duplicate_seeds,
    add_seed_to_history,
    format_time_ago,
    search_history_by_seed,
    get_history_statistics,
    export_history_to_text,
    import_seeds_from_list,
)


class TestSeedHistoryNode:
    """Test SeedHistoryNode functionality."""

    def test_node_structure(self):
        """Test that node has correct ComfyUI structure."""
        # Test class attributes
        assert hasattr(SeedHistoryNode, "INPUT_TYPES")
        assert hasattr(SeedHistoryNode, "RETURN_TYPES")
        assert hasattr(SeedHistoryNode, "RETURN_NAMES")
        assert hasattr(SeedHistoryNode, "FUNCTION")
        assert hasattr(SeedHistoryNode, "CATEGORY")

        # Test input types structure
        input_types = SeedHistoryNode.INPUT_TYPES()
        assert "required" in input_types
        assert "seed" in input_types["required"]

        # Test seed input configuration
        seed_config = input_types["required"]["seed"]
        assert seed_config[0] == "INT"
        assert isinstance(seed_config[1], dict)
        assert "default" in seed_config[1]
        assert "min" in seed_config[1]
        assert "max" in seed_config[1]
        assert seed_config[1]["min"] == 0
        assert seed_config[1]["max"] == 0xFFFFFFFF  # 2**32 - 1

        # Test return types
        assert SeedHistoryNode.RETURN_TYPES == ("INT",)
        assert SeedHistoryNode.RETURN_NAMES == ("seed",)
        assert SeedHistoryNode.FUNCTION == "output_seed"
        assert SeedHistoryNode.CATEGORY == "🫶 ComfyAssets/🌱 Seeds"

    def test_output_seed_valid_input(self):
        """Test seed output with valid input."""
        node = SeedHistoryNode()

        # Test various valid seeds
        test_seeds = [0, 12345, 999999, 0xFFFFFFFF]  # 2**32 - 1

        for seed in test_seeds:
            result = node.output_seed(seed)
            assert isinstance(result, tuple)
            assert len(result) == 1
            assert result[0] == seed

    def test_output_seed_invalid_input(self):
        """Test seed output with invalid input."""
        node = SeedHistoryNode()

        # Test invalid seeds (negative values)
        result = node.output_seed(-1)
        assert result == (12345,)  # Fallback

        # Test seeds too large
        result = node.output_seed(0xFFFFFFFF + 1)  # 2**32
        assert result == (12345,)  # Fallback

    def test_generate_new_seed(self):
        """Test random seed generation."""
        node = SeedHistoryNode()

        # Generate multiple seeds
        seeds = []
        for _ in range(10):
            seed = node.generate_new_seed()
            seeds.append(seed)

        # Test all seeds are valid
        for seed in seeds:
            assert validate_seed_value(seed)

        # Test seeds are different (probabilistically)
        assert len(set(seeds)) > 5  # Should have some variety

    def test_validate_seed_input(self):
        """Test seed validation."""
        node = SeedHistoryNode()

        # Valid seeds
        assert node.validate_seed_input(0)
        assert node.validate_seed_input(12345)
        assert node.validate_seed_input(0xFFFFFFFF)  # 2**32 - 1

        # Invalid seeds
        assert not node.validate_seed_input(-1)
        assert not node.validate_seed_input(0xFFFFFFFF + 1)  # 2**32
        assert not node.validate_seed_input(None)

    def test_get_seed_info(self):
        """Test seed information generation."""
        node = SeedHistoryNode()

        # Test various seed types
        info_zero = node.get_seed_info(0)
        assert "zero" in info_zero.lower()

        info_default = node.get_seed_info(12345)
        assert "default" in info_default.lower()

        info_power_of_2 = node.get_seed_info(1024)
        assert "power of 2" in info_power_of_2.lower()

        # Test invalid seed
        info_invalid = node.get_seed_info(-1)
        assert "invalid" in info_invalid.lower()

    def test_seed_range_info(self):
        """Test seed range information."""
        node = SeedHistoryNode()

        range_info = node.get_seed_range_info()
        assert "Valid range" in range_info
        # Check for the hex representation which should be in the string
        assert "0xffffffff" in range_info.lower()  # 2**32 - 1

    def test_class_methods(self):
        """Test class methods."""
        # Test default seed
        default_seed = SeedHistoryNode.get_default_seed()
        assert default_seed == 12345

        # Test range checking
        assert SeedHistoryNode.is_seed_in_range(0)
        assert SeedHistoryNode.is_seed_in_range(12345)
        assert SeedHistoryNode.is_seed_in_range(0xFFFFFFFF)  # 2**32 - 1
        assert not SeedHistoryNode.is_seed_in_range(-1)
        assert not SeedHistoryNode.is_seed_in_range(0xFFFFFFFF + 1)  # 2**32


class TestSeedHistoryLogic:
    """Test seed history logic functions."""

    def test_generate_random_seed(self):
        """Test random seed generation."""
        # Generate multiple seeds
        seeds = [generate_random_seed() for _ in range(100)]

        # Test all seeds are valid
        for seed in seeds:
            assert validate_seed_value(seed)

        # Test seeds have variety
        assert len(set(seeds)) > 50  # Should have good variety

    def test_validate_seed_value(self):
        """Test seed validation logic."""
        # Valid seeds
        assert validate_seed_value(0)
        assert validate_seed_value(12345)
        assert validate_seed_value(0xFFFFFFFF)  # 2**32 - 1

        # Invalid seeds
        assert not validate_seed_value(-1)
        assert not validate_seed_value(0xFFFFFFFF + 1)  # 2**32
        assert not validate_seed_value(None)
        assert not validate_seed_value("invalid")
        assert not validate_seed_value([])

    def test_sanitize_seed_value(self):
        """Test seed sanitization."""
        # Valid seeds should pass through
        assert sanitize_seed_value(12345) == 12345
        assert sanitize_seed_value(0) == 0
        assert sanitize_seed_value(0xFFFFFFFF) == 0xFFFFFFFF  # 2**32 - 1

        # String numbers should convert
        assert sanitize_seed_value("12345") == 12345
        assert sanitize_seed_value("0") == 0

        # Out of range should clamp
        assert sanitize_seed_value(-100) == 0
        assert sanitize_seed_value(0xFFFFFFFF + 100) == 0xFFFFFFFF  # clamp to 2**32 - 1

        # Invalid should raise
        try:
            sanitize_seed_value(None)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

        try:
            sanitize_seed_value("invalid")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_create_history_entry(self):
        """Test history entry creation."""
        seed = 12345
        timestamp = time.time()

        # With explicit timestamp
        entry = create_history_entry(seed, timestamp)
        assert entry["seed"] == seed
        assert entry["timestamp"] == timestamp
        assert "dateString" in entry

        # With auto timestamp
        entry_auto = create_history_entry(seed)
        assert entry_auto["seed"] == seed
        assert "timestamp" in entry_auto
        assert "dateString" in entry_auto

    def test_filter_duplicate_seeds(self):
        """Test duplicate seed filtering."""
        seed = 12345
        current_time = time.time()

        # Empty history should not filter
        assert not filter_duplicate_seeds([], seed, 500)

        # Recent duplicate should filter
        recent_entry = create_history_entry(seed, current_time - 0.1)
        history = [recent_entry]
        assert filter_duplicate_seeds(history, seed, 500)

        # Old duplicate should not filter
        old_entry = create_history_entry(seed, current_time - 1.0)
        history = [old_entry]
        assert not filter_duplicate_seeds(history, seed, 500)

        # Different seed should not filter
        different_entry = create_history_entry(54321, current_time - 0.1)
        history = [different_entry]
        assert not filter_duplicate_seeds(history, seed, 500)

    def test_add_seed_to_history(self):
        """Test adding seeds to history."""
        history = []

        # Add first seed
        new_history, was_added = add_seed_to_history(history, 12345)
        assert was_added
        assert len(new_history) == 1
        assert new_history[0]["seed"] == 12345

        # Add different seed
        new_history2, was_added2 = add_seed_to_history(new_history, 54321)
        assert was_added2
        assert len(new_history2) == 2
        assert new_history2[0]["seed"] == 54321  # Most recent first

        # Add duplicate (should remove old and add new)
        time.sleep(0.6)  # Wait past dedup window
        new_history3, was_added3 = add_seed_to_history(new_history2, 12345)
        assert was_added3
        assert len(new_history3) == 2
        assert new_history3[0]["seed"] == 12345  # Most recent first

        # Test max history limit
        history_long = []
        for i in range(15):
            history_long, _ = add_seed_to_history(history_long, i, max_history=10)
            time.sleep(0.001)  # Small delay to avoid dedup

        assert len(history_long) == 10

    def test_format_time_ago(self):
        """Test time ago formatting."""
        now = time.time()

        # Recent times
        assert "s ago" in format_time_ago(now - 30)
        assert "m ago" in format_time_ago(now - 300)
        assert "h ago" in format_time_ago(now - 7200)
        assert "d ago" in format_time_ago(now - 86400)

    def test_search_history_by_seed(self):
        """Test history search."""
        history = [
            create_history_entry(12345),
            create_history_entry(54321),
            create_history_entry(99999),
        ]

        # Found seed
        result = search_history_by_seed(history, 54321)
        assert result is not None
        assert result["seed"] == 54321

        # Not found seed
        result = search_history_by_seed(history, 11111)
        assert result is None

    def test_get_history_statistics(self):
        """Test history statistics."""
        # Empty history
        stats = get_history_statistics([])
        assert stats["total_seeds"] == 0
        assert stats["unique_seeds"] == 0

        # History with data
        now = time.time()
        history = [
            create_history_entry(12345, now - 3600),
            create_history_entry(54321, now - 1800),
            create_history_entry(12345, now),  # Duplicate
        ]

        stats = get_history_statistics(history)
        assert stats["total_seeds"] == 3
        assert stats["unique_seeds"] == 2
        assert stats["time_span_hours"] == 1.0

    def test_export_history_to_text(self):
        """Test history export."""
        # Empty history
        text = export_history_to_text([])
        assert "Empty" in text

        # History with data
        history = [create_history_entry(12345), create_history_entry(54321)]

        text = export_history_to_text(history)
        assert "12345" in text
        assert "54321" in text
        assert "Total seeds: 2" in text

    def test_import_seeds_from_list(self):
        """Test importing seeds from list."""
        seed_list = [12345, 54321, 99999]

        history = import_seeds_from_list(seed_list)
        assert len(history) == 3

        # Check seeds are in correct order (newest first)
        assert history[0]["seed"] == 12345
        assert history[1]["seed"] == 54321
        assert history[2]["seed"] == 99999

        # Check timestamps are spaced
        assert history[0]["timestamp"] > history[1]["timestamp"]
        assert history[1]["timestamp"] > history[2]["timestamp"]


class TestSeedHistoryIntegration:
    """Test integration scenarios."""

    def test_complete_workflow(self):
        """Test complete seed history workflow."""
        node = SeedHistoryNode()

        # Test basic seed output
        result = node.output_seed(12345)
        assert result == (12345,)

        # Test seed generation
        new_seed = node.generate_new_seed()
        assert validate_seed_value(new_seed)

        # Test seed info
        info = node.get_seed_info(new_seed)
        assert str(new_seed) in info

    def test_history_management(self):
        """Test history management operations."""
        history = []

        # Add seeds over time
        seeds = [12345, 54321, 99999, 11111, 22222]
        for seed in seeds:
            history, was_added = add_seed_to_history(history, seed)
            assert was_added
            time.sleep(0.001)  # Avoid dedup

        # Check history order (newest first)
        assert history[0]["seed"] == 22222
        assert history[-1]["seed"] == 12345

        # Test search
        found = search_history_by_seed(history, 99999)
        assert found is not None

        # Test statistics
        stats = get_history_statistics(history)
        assert stats["total_seeds"] == 5
        assert stats["unique_seeds"] == 5

    def test_error_handling(self):
        """Test error handling scenarios."""
        node = SeedHistoryNode()

        # Test with invalid seeds
        result = node.output_seed(-1)
        assert result == (12345,)  # Fallback

        # Test validation
        assert not node.validate_seed_input(None)
        assert not node.validate_seed_input("invalid")

        # Test history with invalid seeds
        history = []
        history, was_added = add_seed_to_history(history, -1)
        assert not was_added
        assert len(history) == 0
