import sys
from unittest.mock import call, patch, MagicMock

import pytest

# Mock comfy modules
mock_mm = MagicMock()
sys.modules["comfy"] = MagicMock()
sys.modules["comfy.model_management"] = mock_mm

from kikotools.tools.kiko_purge_vram.logic import (
    MODES,
    memory_view,
    plan_steps,
    read_memory_mb,
    resolve_mode,
    run_steps,
    should_skip,
)

# Ensure mm is available in the logic module after import
import kikotools.tools.kiko_purge_vram.logic as logic_module

logic_module.mm = mock_mm

GIB = 1024**3


@pytest.fixture
def fresh_mm():
    mm = MagicMock()
    with (
        patch.object(logic_module, "mm", mm),
        patch.object(logic_module, "COMFY_AVAILABLE", True),
    ):
        yield mm


class TestModes:
    def test_resolve_mode_new_and_legacy(self):
        assert resolve_mode("all") == ("all", None)
        assert resolve_mode("soft") == ("all", "soft")
        assert resolve_mode("aggressive") == ("all", "aggressive")
        assert resolve_mode("models_only") == ("models", "models_only")
        assert resolve_mode("cache_only") == ("cache", "cache_only")

    def test_resolve_mode_rejects_unknown(self):
        with pytest.raises(ValueError, match="all, models, cache"):
            resolve_mode("turbo")

    def test_plan_steps(self):
        assert plan_steps("all", True) == {"models": True, "gc": True, "cache": True}
        assert plan_steps("models", True) == {
            "models": True,
            "gc": True,
            "cache": False,
        }
        assert plan_steps("cache", False) == {
            "models": False,
            "gc": False,
            "cache": True,
        }

    def test_memory_view(self):
        assert [memory_view(m) for m in MODES] == ["comfy", "comfy", "driver"]


class TestRunSteps:
    def test_run_steps_order_all(self, fresh_mm):
        parent = MagicMock()
        parent.attach_mock(fresh_mm, "mm")
        with patch("gc.collect") as collect:
            parent.attach_mock(collect, "collect")
            run_steps(plan_steps("all", True))

        assert parent.mock_calls == [
            call.mm.unload_all_models(),
            call.collect(),
            call.mm.soft_empty_cache(True),
        ]

    def test_run_steps_models_skips_cache(self, fresh_mm):
        with patch("gc.collect"):
            run_steps(plan_steps("models", True))

        fresh_mm.unload_all_models.assert_called_once()
        fresh_mm.soft_empty_cache.assert_not_called()

    def test_run_steps_cache_skips_unload(self, fresh_mm):
        with patch("gc.collect") as collect:
            run_steps(plan_steps("cache", True))

        fresh_mm.unload_all_models.assert_not_called()
        collect.assert_not_called()
        fresh_mm.soft_empty_cache.assert_called_once_with(True)

    def test_run_steps_without_comfy_only_collects(self, fresh_mm):
        logic_module.COMFY_AVAILABLE = False
        try:
            with patch("gc.collect") as collect:
                run_steps(plan_steps("all", True))
        finally:
            logic_module.COMFY_AVAILABLE = True

        collect.assert_called_once()
        assert fresh_mm.mock_calls == []


class TestReadMemory:
    def test_read_memory_comfy_view(self, fresh_mm):
        fresh_mm.get_free_memory.return_value = 6 * GIB
        fresh_mm.get_total_memory.return_value = 24 * GIB

        assert read_memory_mb("comfy") == (6144.0, 24576.0)

    def test_read_memory_driver_view(self, fresh_mm):
        fresh_mm.get_free_memory.return_value = (8 * GIB, 2 * GIB)
        fresh_mm.get_total_memory.return_value = 24 * GIB

        free_mb, total_mb = read_memory_mb("driver")

        assert free_mb == 6144.0
        assert total_mb == 24576.0
        assert fresh_mm.get_free_memory.call_args.kwargs == {"torch_free_too": True}

    def test_read_memory_returns_none_when_mm_raises(self, fresh_mm):
        fresh_mm.get_torch_device.side_effect = RuntimeError

        assert read_memory_mb("comfy") is None

    def test_read_memory_returns_none_without_comfy(self, fresh_mm):
        logic_module.COMFY_AVAILABLE = False
        try:
            assert read_memory_mb("comfy") is None
        finally:
            logic_module.COMFY_AVAILABLE = True


def test_should_skip():
    assert should_skip(0, 9000.0) is False
    assert should_skip(4000, 9000.0) is True
    assert should_skip(4000, 4000.0) is True
    assert should_skip(4000, 3999.0) is False
    assert should_skip(4000, None) is False


class TestKikoPurgeVRAMNode:
    @patch("kikotools.tools.kiko_purge_vram.node.format_memory_report")
    @patch("kikotools.tools.kiko_purge_vram.node.purge_memory")
    @patch("kikotools.tools.kiko_purge_vram.node.get_memory_stats")
    @patch("kikotools.tools.kiko_purge_vram.node.should_purge")
    def test_node_execute_with_threshold(
        self, mock_should_purge, mock_stats, mock_purge, mock_format
    ):
        from kikotools.tools.kiko_purge_vram.node import KikoPurgeVRAM

        mock_should_purge.return_value = (
            True,
            "Memory usage (5000.0 MB) exceeds threshold (4000 MB)",
        )
        mock_stats.side_effect = [
            {
                "used_mb": 5000,
                "free_mb": 3000,
                "total_mb": 8000,
                "used_percent": 62.5,
                "cuda_available": True,
            },
            {
                "used_mb": 2000,
                "free_mb": 6000,
                "total_mb": 8000,
                "used_percent": 25,
                "cuda_available": True,
            },
        ]
        mock_purge.return_value = 3000
        mock_format.return_value = "Memory Purge Report\n-------------------\nMode: soft\nMemory Freed: 3000.0 MB"

        node = KikoPurgeVRAM()
        test_input = "test_data"

        result, report = node.purge_vram(
            anything=test_input,
            mode="soft",
            report_memory=True,
            memory_threshold_mb=4000,
        )

        assert result == test_input
        assert "Memory Freed: 3000.0 MB" in report
        mock_purge.assert_called_once_with(mode="soft", unload_models=False)

    @patch("kikotools.tools.kiko_purge_vram.logic.get_memory_stats")
    def test_node_skip_below_threshold(self, mock_stats):
        from kikotools.tools.kiko_purge_vram.node import KikoPurgeVRAM

        mock_stats.return_value = {
            "used_mb": 2000,
            "free_mb": 6000,
            "total_mb": 8000,
            "used_percent": 25,
            "cuda_available": True,
        }

        node = KikoPurgeVRAM()
        test_input = "test_data"

        with patch("kikotools.tools.kiko_purge_vram.logic.purge_memory") as mock_purge:
            result, report = node.purge_vram(
                anything=test_input,
                mode="soft",
                report_memory=True,
                memory_threshold_mb=3000,
            )

            assert result == test_input
            assert "below threshold" in report.lower()
            mock_purge.assert_not_called()

    def test_node_input_types(self):
        from kikotools.tools.kiko_purge_vram.node import KikoPurgeVRAM

        input_types = KikoPurgeVRAM.INPUT_TYPES()

        assert "required" in input_types
        assert "optional" in input_types
        assert "anything" in input_types["required"]
        assert "mode" in input_types["required"]
        assert "report_memory" in input_types["required"]
        assert "memory_threshold_mb" in input_types["optional"]

    def test_node_properties(self):
        from kikotools.tools.kiko_purge_vram.node import KikoPurgeVRAM

        assert KikoPurgeVRAM.FUNCTION == "purge_vram"
        assert KikoPurgeVRAM.CATEGORY == "🫶 ComfyAssets/🛠️ Utils"
        assert KikoPurgeVRAM.OUTPUT_NODE is True
        assert len(KikoPurgeVRAM.RETURN_TYPES) == 2
        assert KikoPurgeVRAM.RETURN_NAMES == ("passthrough", "memory_report")


class TestPurgeIsChanged:
    def test_is_changed_is_nan_so_cache_never_hits(self):
        from kikotools.tools.kiko_purge_vram.node import KikoPurgeVRAM

        value = KikoPurgeVRAM.IS_CHANGED(anything=1, mode="soft", report_memory=True)
        assert value != value  # NaN is never equal to itself
