import sys
from unittest.mock import patch, MagicMock

import pytest

# Mock comfy modules
mock_mm = MagicMock()
sys.modules["comfy"] = MagicMock()
sys.modules["comfy.model_management"] = mock_mm

from kikotools.tools.kiko_purge_vram.logic import (
    purge_memory,
    get_memory_stats,
    format_memory_report,
)

# Ensure mm is available in the logic module after import
import kikotools.tools.kiko_purge_vram.logic as logic_module

logic_module.mm = mock_mm


class TestMemoryStats:
    @patch("torch.cuda.is_available")
    @patch("torch.cuda.mem_get_info")
    def test_get_memory_stats_with_cuda(self, mock_mem_info, mock_cuda_available):
        mock_cuda_available.return_value = True
        mock_mem_info.return_value = (4000000000, 8000000000)  # 4GB free, 8GB total

        stats = get_memory_stats()

        assert stats["cuda_available"] is True
        assert stats["free_mb"] == pytest.approx(3814.7, rel=0.1)
        assert stats["total_mb"] == pytest.approx(7629.4, rel=0.1)
        assert stats["used_mb"] == pytest.approx(3814.7, rel=0.1)
        assert stats["used_percent"] == pytest.approx(50.0, rel=0.1)

    @patch("torch.cuda.is_available")
    def test_get_memory_stats_without_cuda(self, mock_cuda_available):
        mock_cuda_available.return_value = False

        stats = get_memory_stats()

        assert stats["cuda_available"] is False
        assert stats["free_mb"] == 0
        assert stats["total_mb"] == 0
        assert stats["used_mb"] == 0
        assert stats["used_percent"] == 0


class TestMemoryPurge:
    @patch("torch.cuda.is_available")
    @patch("torch.cuda.empty_cache")
    @patch("torch.cuda.ipc_collect")
    @patch("gc.collect")
    def test_purge_memory_soft_mode(
        self, mock_gc, mock_ipc, mock_empty_cache, mock_cuda
    ):
        mock_cuda.return_value = True

        with patch(
            "kikotools.tools.kiko_purge_vram.logic.get_memory_stats"
        ) as mock_stats:
            mock_stats.side_effect = [
                {"used_mb": 4000, "free_mb": 4000},
                {"used_mb": 2000, "free_mb": 6000},
            ]

            freed_mb = purge_memory(mode="soft", unload_models=False)

            mock_gc.assert_called_once()
            mock_empty_cache.assert_called_once()
            mock_ipc.assert_not_called()
            assert freed_mb == 2000

    @patch("torch.cuda.is_available")
    @patch("torch.cuda.empty_cache")
    @patch("torch.cuda.ipc_collect")
    @patch("torch.cuda.synchronize")
    @patch("gc.collect")
    def test_purge_memory_aggressive_mode(
        self, mock_gc, mock_sync, mock_ipc, mock_empty_cache, mock_cuda
    ):
        mock_cuda.return_value = True

        with patch(
            "kikotools.tools.kiko_purge_vram.logic.get_memory_stats"
        ) as mock_stats:
            mock_stats.side_effect = [
                {"used_mb": 4000, "free_mb": 4000},
                {"used_mb": 1500, "free_mb": 6500},
            ]

            freed_mb = purge_memory(mode="aggressive", unload_models=False)

            assert mock_gc.call_count == 2
            mock_empty_cache.assert_called()
            mock_ipc.assert_called_once()
            mock_sync.assert_called_once()
            assert freed_mb == 2500

    @patch("kikotools.tools.kiko_purge_vram.logic.COMFY_AVAILABLE", True)
    @patch("torch.cuda.is_available")
    @patch("gc.collect")
    def test_purge_memory_models_only(self, mock_gc, mock_cuda):
        mock_cuda.return_value = True

        with patch(
            "kikotools.tools.kiko_purge_vram.logic.get_memory_stats"
        ) as mock_stats:
            mock_stats.side_effect = [
                {"used_mb": 6000, "free_mb": 2000},
                {"used_mb": 1000, "free_mb": 7000},
            ]

            freed_mb = purge_memory(mode="models_only", unload_models=True)

            mock_mm.unload_all_models.assert_called_once()
            mock_mm.soft_empty_cache.assert_called_once()
            mock_gc.assert_called()
            assert freed_mb == 5000

    @patch("torch.cuda.is_available")
    @patch("torch.cuda.empty_cache")
    @patch("gc.collect")
    def test_purge_memory_cache_only(self, mock_gc, mock_empty_cache, mock_cuda):
        mock_cuda.return_value = True

        with patch(
            "kikotools.tools.kiko_purge_vram.logic.get_memory_stats"
        ) as mock_stats:
            mock_stats.side_effect = [
                {"used_mb": 3000, "free_mb": 5000},
                {"used_mb": 2500, "free_mb": 5500},
            ]

            freed_mb = purge_memory(mode="cache_only", unload_models=False)

            mock_gc.assert_not_called()
            mock_empty_cache.assert_called_once()
            assert freed_mb == 500

    @patch("torch.cuda.is_available")
    def test_purge_memory_no_cuda(self, mock_cuda):
        mock_cuda.return_value = False

        with patch("gc.collect") as mock_gc:
            freed_mb = purge_memory(mode="soft", unload_models=False)

            mock_gc.assert_called_once()
            assert freed_mb == 0


class TestMemoryReport:
    def test_format_memory_report_with_improvement(self):
        before = {
            "used_mb": 4000,
            "free_mb": 4000,
            "total_mb": 8000,
            "used_percent": 50,
        }
        after = {"used_mb": 2000, "free_mb": 6000, "total_mb": 8000, "used_percent": 25}

        report = format_memory_report(before, after, mode="soft", elapsed_ms=150)

        assert "Memory Purge Report" in report
        assert "Mode: soft" in report
        assert "Memory Freed: 2000.0 MB" in report
        assert "Before: 4000.0 MB used (50.0%)" in report
        assert "After: 2000.0 MB used (25.0%)" in report
        assert "Time: 150.0ms" in report

    def test_format_memory_report_no_improvement(self):
        before = {
            "used_mb": 2000,
            "free_mb": 6000,
            "total_mb": 8000,
            "used_percent": 25,
        }
        after = {"used_mb": 2000, "free_mb": 6000, "total_mb": 8000, "used_percent": 25}

        report = format_memory_report(before, after, mode="cache_only", elapsed_ms=50)

        assert "Memory Freed: 0.0 MB" in report
        assert "Time: 50.0ms" in report

    def test_format_memory_report_no_cuda(self):
        before = {
            "used_mb": 0,
            "free_mb": 0,
            "total_mb": 0,
            "used_percent": 0,
            "cuda_available": False,
        }
        after = {
            "used_mb": 0,
            "free_mb": 0,
            "total_mb": 0,
            "used_percent": 0,
            "cuda_available": False,
        }

        report = format_memory_report(before, after, mode="soft", elapsed_ms=10)

        assert "CUDA not available" in report


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
