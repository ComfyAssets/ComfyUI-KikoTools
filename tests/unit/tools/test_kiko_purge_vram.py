import inspect
import logging
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
    repair_loaded_models,
    resolve_mode,
    run_steps,
    should_skip,
    unload_models_safely,
)

# Ensure mm is available in the logic module after import
import kikotools.tools.kiko_purge_vram.logic as logic_module

logic_module.mm = mock_mm

GIB = 1024**3


@pytest.fixture
def fresh_mm():
    mm = MagicMock()
    mm.is_oom.return_value = False
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
        assert plan_steps("cache", True) == {
            "models": False,
            "gc": True,
            "cache": True,
        }

    def test_memory_view(self):
        assert [memory_view(m) for m in MODES] == ["comfy", "comfy", "driver"]


class FakeLoaded:
    def __init__(
        self,
        name,
        loaded=True,
        patcher=True,
        on_unload=None,
        raise_before_clearing=False,
        shared_model=None,
    ):
        self.name = name
        self.real_model = (lambda: object()) if loaded else None
        self.model = shared_model or (object() if patcher else None)
        self.on_unload = on_unload
        self.raise_before_clearing = raise_before_clearing
        self.unload_calls = 0

    def __eq__(self, other):
        # ComfyUI's LoadedModel compares patchers, not entries.
        return isinstance(other, FakeLoaded) and self.model is other.model

    __hash__ = object.__hash__

    def model_unload(self):
        self.unload_calls += 1
        if self.on_unload and self.raise_before_clearing:
            self.on_unload()
        self.real_model = None
        if self.on_unload:
            self.on_unload()


class TestSafeUnload:
    def test_unload_models_safely_unloads_and_removes_all(self, fresh_mm):
        entries = [FakeLoaded(n) for n in "abc"]
        fresh_mm.current_loaded_models = list(entries)

        unload_models_safely()

        assert [e.unload_calls for e in entries] == [1, 1, 1]
        assert fresh_mm.current_loaded_models == []

    def test_unload_delegates_to_unload_all_models_after_the_drain(self, fresh_mm):
        entries = [FakeLoaded(n) for n in "ab"]
        fresh_mm.current_loaded_models = list(entries)
        order = []
        for entry in entries:
            entry.on_unload = lambda name=entry.name: order.append(name)
        fresh_mm.unload_all_models.side_effect = lambda: order.append("unload_all")

        unload_models_safely()

        assert order == ["a", "b", "unload_all"]
        fresh_mm.unload_all_models.assert_called_once_with()

    def test_unload_delegates_even_when_nothing_needed_unloading(self, fresh_mm):
        fresh_mm.current_loaded_models = [
            FakeLoaded("x", loaded=False),
            FakeLoaded("y", patcher=False),
        ]

        unload_models_safely()

        fresh_mm.unload_all_models.assert_called_once_with()

    def test_unload_removes_by_identity_when_entries_share_a_patcher(self, fresh_mm):
        shared = object()
        a = FakeLoaded("a", shared_model=shared)
        b = FakeLoaded("b", shared_model=shared)
        assert a == b
        b.real_model = None
        fresh_mm.current_loaded_models = [a, b]

        unload_models_safely()

        assert (a.unload_calls, b.unload_calls) == (1, 0)
        assert fresh_mm.current_loaded_models == []

    def test_repair_removes_by_identity_when_entries_share_a_patcher(self, fresh_mm):
        shared = object()
        good = FakeLoaded("good", shared_model=shared)
        half = FakeLoaded("half", loaded=False, shared_model=shared)
        fresh_mm.current_loaded_models = [good, half]

        assert repair_loaded_models() == 1
        assert fresh_mm.current_loaded_models[0] is good
        assert len(fresh_mm.current_loaded_models) == 1

    def test_unload_survives_list_shrinking_mid_loop(self, fresh_mm):
        loaded = []
        a = FakeLoaded("a", on_unload=lambda: loaded.remove(c))
        b = FakeLoaded("b")
        c = FakeLoaded("c")
        loaded.extend([a, b, c])
        fresh_mm.current_loaded_models = loaded

        unload_models_safely()

        assert loaded == []
        assert (a.unload_calls, b.unload_calls, c.unload_calls) == (1, 1, 0)

    def test_unload_skips_entries_already_unloaded_or_dead(self, fresh_mm):
        x = FakeLoaded("x", loaded=False)
        y = FakeLoaded("y", patcher=False)
        fresh_mm.current_loaded_models = [x, y]

        unload_models_safely()

        assert fresh_mm.current_loaded_models == []
        assert (x.unload_calls, y.unload_calls) == (0, 0)

    def test_unload_falls_back_without_a_list(self, fresh_mm):
        unload_models_safely()

        fresh_mm.unload_all_models.assert_called_once_with()

    def test_unload_empties_cache_once_after_unloading(self, fresh_mm):
        fresh_mm.current_loaded_models = [FakeLoaded("a"), FakeLoaded("b")]

        unload_models_safely()

        fresh_mm.soft_empty_cache.assert_called_once_with()

    def test_unload_does_not_empty_cache_when_nothing_unloaded(self, fresh_mm):
        fresh_mm.current_loaded_models = [
            FakeLoaded("x", loaded=False),
            FakeLoaded("y", patcher=False),
        ]

        unload_models_safely()

        fresh_mm.soft_empty_cache.assert_not_called()

    def test_repair_removes_half_unloaded_entries(self, fresh_mm):
        first, half, last = (
            FakeLoaded("a"),
            FakeLoaded("h", loaded=False),
            FakeLoaded("b"),
        )
        fresh_mm.current_loaded_models = [first, half, last]

        assert repair_loaded_models() == 1
        assert fresh_mm.current_loaded_models == [first, last]

    def test_repair_without_a_list_returns_zero(self, fresh_mm):
        assert repair_loaded_models() == 0


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
        collect.assert_called_once()
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

    @pytest.mark.parametrize("device_type", ["cpu", "mps"])
    def test_read_memory_driver_view_uses_comfy_figure_on_cpu_and_mps(
        self, fresh_mm, device_type
    ):
        fresh_mm.get_torch_device.return_value.type = device_type
        fresh_mm.get_free_memory.return_value = 6 * GIB
        fresh_mm.get_total_memory.return_value = 24 * GIB

        assert read_memory_mb("driver") == (6144.0, 24576.0)
        assert fresh_mm.get_free_memory.call_args.kwargs == {}

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


def _node():
    from kikotools.tools.kiko_purge_vram.node import KikoPurgeVRAM

    return KikoPurgeVRAM


def _node_module():
    import kikotools.tools.kiko_purge_vram.node as node_module

    return node_module


def _set_memory(mm, frees_gib, total_gib=24):
    mm.get_free_memory.side_effect = [int(f * GIB) for f in frees_gib]
    mm.get_total_memory.return_value = total_gib * GIB


class TestNodeDefinition:
    def test_input_types(self):
        types = _node().INPUT_TYPES()

        assert list(types["required"]) == ["mode", "report_memory"]
        assert types["required"]["mode"][0] == ["all", "models", "cache"]
        assert types["required"]["mode"][1]["default"] == "all"
        assert list(types["optional"]) == [
            "anything",
            "memory_threshold_mb",
            "collect_garbage",
            "every_run",
        ]
        opts = types["optional"]["memory_threshold_mb"][1]
        assert (opts["default"], opts["min"], opts["max"], opts["step"]) == (
            0,
            0,
            262144,
            100,
        )
        assert types["optional"]["collect_garbage"][1]["default"] is True
        assert types["optional"]["every_run"][1]["default"] is True

    def test_properties(self):
        node = _node()

        assert node.FUNCTION == "purge_vram"
        assert node.CATEGORY == "🫶 ComfyAssets/🛠️ Utils"
        assert node.OUTPUT_NODE is True
        assert len(node.RETURN_TYPES) == 2
        assert node.RETURN_NAMES == ("passthrough", "memory_report")

    def test_description_credits_pixaroma(self):
        credit = (
            "Behaviour based on Free VRAM Pixaroma from ComfyUI-Pixaroma "
            "by Pixaroma."
        )
        assert credit in _node().DESCRIPTION

    def test_validate_inputs_accepts_linked_input(self):
        assert _node().VALIDATE_INPUTS(None) is True

    def test_validate_inputs_signature_names_only_mode(self):
        spec = inspect.getfullargspec(_node().VALIDATE_INPUTS)

        assert "mode" in spec.args
        assert spec.varkw is None

    def test_is_changed_linked_every_run_counts_as_on(self):
        value = _node().IS_CHANGED(every_run=None, mode="all")

        assert value != value

    def test_is_changed_tracks_threshold_and_garbage(self):
        node = _node()
        base = dict(every_run=False, mode="all")
        first = node.IS_CHANGED(memory_threshold_mb=0, collect_garbage=True, **base)

        assert first != node.IS_CHANGED(
            memory_threshold_mb=500, collect_garbage=True, **base
        )
        assert first != node.IS_CHANGED(
            memory_threshold_mb=0, collect_garbage=False, **base
        )

    def test_validate_inputs(self):
        node = _node()

        assert node.VALIDATE_INPUTS("all") is True
        assert node.VALIDATE_INPUTS("soft") is True
        message = node.VALIDATE_INPUTS("turbo")
        assert isinstance(message, str)
        assert "all, models, cache" in message

    def test_is_changed(self):
        node = _node()

        always = node.IS_CHANGED(every_run=True, mode="all")
        assert always != always
        default = node.IS_CHANGED(mode="all")
        assert default != default

        kwargs = dict(every_run=False, memory_threshold_mb=0, collect_garbage=True)
        first = node.IS_CHANGED(mode="all", **kwargs)
        assert first == node.IS_CHANGED(mode="all", **kwargs)
        assert first != node.IS_CHANGED(mode="cache", **kwargs)


class TestPurgeVram:
    def test_unwired_does_nothing(self, fresh_mm):
        result, report = _node()().purge_vram("all", True)

        assert result is None
        assert "Nothing wired in" in report
        assert fresh_mm.mock_calls == []

    def test_falsy_input_counts_as_wired(self, fresh_mm):
        _set_memory(fresh_mm, [2, 10])

        result, _ = _node()().purge_vram("all", True, anything=0)

        assert result == 0
        fresh_mm.unload_all_models.assert_called_once_with()

    def test_all_mode_runs_and_reports(self, fresh_mm):
        _set_memory(fresh_mm, [2, 10])

        result, report = _node()().purge_vram("all", True, anything="x")

        assert result == "x"
        assert "Mode: all" in report
        assert "Memory Freed: 8192.0 MB" in report
        assert "Before: 2048.0 MB free of 24576.0 MB" in report
        assert "After: 10240.0 MB free of 24576.0 MB" in report
        assert "Time: " in report

    def test_legacy_mode_is_mapped_and_named(self, fresh_mm):
        _set_memory(fresh_mm, [2, 10])

        _, report = _node()().purge_vram("soft", True, anything="x")

        fresh_mm.unload_all_models.assert_called_once_with()
        assert "Mode: all (from legacy 'soft')" in report

    def test_threshold_skips_when_enough_free(self, fresh_mm):
        _set_memory(fresh_mm, [9000 / 1024])

        result, report = _node()().purge_vram(
            "all", True, anything="x", memory_threshold_mb=4000
        )

        assert result == "x"
        fresh_mm.unload_all_models.assert_not_called()
        assert report.startswith("Memory purge skipped:")
        assert "9000.0 MB free" in report
        assert "4000 MB" in report

    def test_threshold_runs_when_memory_unreadable(self, fresh_mm):
        fresh_mm.get_torch_device.side_effect = RuntimeError("no device")

        _, report = _node()().purge_vram(
            "all", True, anything="x", memory_threshold_mb=4000
        )

        fresh_mm.unload_all_models.assert_called_once_with()
        assert "Memory figures unavailable" in report

    def test_cache_mode_uses_driver_view(self, fresh_mm):
        fresh_mm.get_free_memory.return_value = (8 * GIB, 2 * GIB)
        fresh_mm.get_total_memory.return_value = 24 * GIB

        _, report = _node()().purge_vram(
            "cache", True, anything="x", memory_threshold_mb=7000
        )

        fresh_mm.soft_empty_cache.assert_called_once_with(True)
        assert "Memory purge skipped" not in report
        assert "Before: 6144.0 MB free" in report

    def test_report_off_returns_empty_string(self, fresh_mm):
        _set_memory(fresh_mm, [2, 10])

        result, report = _node()().purge_vram("all", False, anything="x")

        assert (result, report) == ("x", "")
        fresh_mm.unload_all_models.assert_called_once_with()

    def test_collect_garbage_switch(self, fresh_mm):
        _set_memory(fresh_mm, [2, 10])

        with patch("gc.collect") as collect:
            _node()().purge_vram("all", False, anything="x", collect_garbage=False)

        collect.assert_not_called()

    @staticmethod
    def _failing_models(fresh_mm):
        def boom():
            raise RuntimeError("boom")

        failing = FakeLoaded("a", on_unload=boom)
        fresh_mm.current_loaded_models = [failing, FakeLoaded("b")]
        _set_memory(fresh_mm, [2, 2])

    def test_step_error_repairs_and_raises(self, fresh_mm):
        self._failing_models(fresh_mm)

        with pytest.raises(RuntimeError) as caught:
            _node()().purge_vram("all", True, anything=1)

        message = str(caught.value)
        assert "Kiko Purge VRAM could not free memory" in message
        assert "boom" in message
        assert "repaired" in message
        assert "1 half-unloaded entry removed" in message
        assert all(e.real_model is not None for e in fresh_mm.current_loaded_models)
        assert isinstance(caught.value.__cause__, RuntimeError)
        assert str(caught.value.__cause__) == "boom"

    def test_step_error_reports_one_removed_entry(self, fresh_mm):
        self._failing_models(fresh_mm)
        with patch.object(_node_module(), "repair_loaded_models", return_value=1):
            with pytest.raises(RuntimeError) as caught:
                _node()().purge_vram("all", True, anything=1)

        assert "1 half-unloaded entry removed" in str(caught.value)

    def test_step_error_reports_many_removed_entries(self, fresh_mm):
        self._failing_models(fresh_mm)
        with patch.object(_node_module(), "repair_loaded_models", return_value=3):
            with pytest.raises(RuntimeError) as caught:
                _node()().purge_vram("all", True, anything=1)

        assert "3 half-unloaded entries removed" in str(caught.value)

    def test_step_error_logs_before_repairing(self, fresh_mm):
        self._failing_models(fresh_mm)
        order = []
        with (
            patch.object(
                _node_module().logger,
                "exception",
                side_effect=lambda *a: order.append("log"),
            ),
            patch.object(
                _node_module(),
                "repair_loaded_models",
                side_effect=lambda: order.append("repair") or 0,
            ),
        ):
            with pytest.raises(RuntimeError):
                _node()().purge_vram("all", True, anything=1)

        assert order == ["log", "repair"]

    def test_out_of_memory_error_is_reraised_unchanged(self, fresh_mm):
        oom = MemoryError("out of memory")

        def boom():
            raise oom

        failing = FakeLoaded("a", on_unload=boom)
        fresh_mm.current_loaded_models = [failing, FakeLoaded("b")]
        fresh_mm.is_oom.return_value = True
        _set_memory(fresh_mm, [2, 2])

        with pytest.raises(MemoryError) as caught:
            _node()().purge_vram("all", True, anything=1)

        assert caught.value is oom
        assert all(e.real_model is not None for e in fresh_mm.current_loaded_models)

    def test_failure_before_real_model_cleared_leaves_entry_and_says_so(self, fresh_mm):
        def boom():
            raise RuntimeError("boom")

        failing = FakeLoaded("a", on_unload=boom, raise_before_clearing=True)
        fresh_mm.current_loaded_models = [failing]
        _set_memory(fresh_mm, [2, 2])

        with pytest.raises(RuntimeError) as caught:
            _node()().purge_vram("all", True, anything=1)

        assert fresh_mm.current_loaded_models == [failing]
        assert "no half-unloaded entries were found" in str(caught.value)

    def test_step_error_logs_traceback(self, fresh_mm, caplog):
        self._failing_models(fresh_mm)

        with caplog.at_level(logging.ERROR):
            with pytest.raises(RuntimeError):
                _node()().purge_vram("all", True, anything=1)

        records = [
            r
            for r in caplog.records
            if r.name == "kikotools.tools.kiko_purge_vram.node"
        ]
        assert len(records) == 1
        assert records[0].exc_info

    def test_step_error_raises_with_report_off(self, fresh_mm):
        self._failing_models(fresh_mm)

        with pytest.raises(RuntimeError, match="could not free memory"):
            _node()().purge_vram("all", False, anything=1)

    def test_skip_with_report_off_returns_empty_and_keeps_models(self, fresh_mm):
        _set_memory(fresh_mm, [9000 / 1024])

        result, report = _node()().purge_vram(
            "all", False, anything="x", memory_threshold_mb=4000
        )

        assert (result, report) == ("x", "")
        fresh_mm.unload_all_models.assert_not_called()
