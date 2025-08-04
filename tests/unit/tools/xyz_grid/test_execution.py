"""Tests for execution flow components."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from kikotools.tools.xyz_grid.controller.execution import (
    GridExecutionState, ExecutionManager
)
from kikotools.tools.xyz_grid.controller.queue_manager import (
    QueuedExecution, GridQueueManager
)


class TestGridExecutionState:
    """Test GridExecutionState class."""
    
    def test_initialization(self):
        """Test state initialization."""
        state = GridExecutionState(
            batch_id="test123",
            total_iterations=12,
            x_count=3,
            y_count=4,
            z_count=1
        )
        
        assert state.batch_id == "test123"
        assert state.total_iterations == 12
        assert state.current_iteration == 0
        assert state.x_index == 0
        assert state.y_index == 0
        assert state.z_index == 0
    
    def test_advance_simple(self):
        """Test advancing through iterations."""
        state = GridExecutionState(
            batch_id="test",
            total_iterations=6,
            x_count=2,
            y_count=3,
            z_count=1
        )
        
        # Test advancing through all positions
        positions = []
        for i in range(6):
            positions.append(state.get_indices())
            state.advance()
        
        expected = [
            (0, 0, 0), (1, 0, 0),  # First row
            (0, 1, 0), (1, 1, 0),  # Second row
            (0, 2, 0), (1, 2, 0),  # Third row
        ]
        assert positions == expected
    
    def test_advance_with_z(self):
        """Test advancing with Z axis."""
        state = GridExecutionState(
            batch_id="test",
            total_iterations=8,
            x_count=2,
            y_count=2,
            z_count=2
        )
        
        # Advance through first grid
        for _ in range(4):
            state.advance()
        
        # Should now be at start of second Z
        assert state.get_indices() == (0, 0, 1)
    
    def test_is_complete(self):
        """Test completion detection."""
        state = GridExecutionState(
            batch_id="test",
            total_iterations=2,
            x_count=2,
            y_count=1
        )
        
        assert not state.is_complete()
        
        state.advance()
        assert not state.is_complete()
        
        state.advance()
        assert state.is_complete()


class TestExecutionManager:
    """Test ExecutionManager class."""
    
    def test_initialize_batch(self):
        """Test batch initialization."""
        manager = ExecutionManager()
        
        x_vals = ["a", "b", "c"]
        y_vals = [1, 2]
        z_vals = ["z1"]
        
        state = manager.initialize_batch("batch1", x_vals, y_vals, z_vals)
        
        assert state.batch_id == "batch1"
        assert state.total_iterations == 6  # 3 * 2 * 1
        assert state.x_count == 3
        assert state.y_count == 2
        assert state.z_count == 1
    
    def test_get_current_values(self):
        """Test getting current values."""
        manager = ExecutionManager()
        
        x_vals = ["model1", "model2"]
        y_vals = [5.0, 7.5]
        z_vals = [""]
        
        # First call should initialize
        x, y, z, xi, yi, zi = manager.get_current_values(
            "batch1", x_vals, y_vals, z_vals
        )
        
        assert x == "model1"
        assert y == 5.0
        assert z == ""
        assert (xi, yi, zi) == (0, 0, 0)
        
        # Advance and get next
        manager.advance_batch("batch1")
        x, y, z, xi, yi, zi = manager.get_current_values(
            "batch1", x_vals, y_vals, z_vals
        )
        
        assert x == "model2"
        assert y == 5.0
        assert (xi, yi, zi) == (1, 0, 0)
    
    def test_should_continue(self):
        """Test continuation checking."""
        manager = ExecutionManager()
        
        # Non-existent batch
        assert not manager.should_continue("nonexistent")
        
        # Initialize small batch
        manager.initialize_batch("batch1", ["a"], ["b"], [""])
        assert manager.should_continue("batch1")
        
        # Complete the batch
        state = manager.execution_states["batch1"]
        state.current_iteration = state.total_iterations
        assert not manager.should_continue("batch1")
    
    def test_cleanup_batch(self):
        """Test batch cleanup."""
        manager = ExecutionManager()
        
        manager.initialize_batch("batch1", ["a"], ["b"], ["c"])
        assert "batch1" in manager.execution_states
        
        manager.cleanup_batch("batch1")
        assert "batch1" not in manager.execution_states


class TestGridQueueManager:
    """Test GridQueueManager class."""
    
    def test_prepare_batch_executions(self):
        """Test preparing batch executions."""
        manager = GridQueueManager()
        
        grid_config = {
            "axes": {
                "x": {"values": ["v1", "v2"], "labels": ["V1", "V2"]},
                "y": {"values": [1, 2, 3], "labels": ["1", "2", "3"]},
                "z": {"values": [""], "labels": [""]},
            },
            "dimensions": {"total_images": 6}
        }
        
        workflow = {"test": "workflow"}
        executions = manager.prepare_batch_executions(
            "batch1", grid_config, 123, workflow
        )
        
        assert len(executions) == 6
        assert all(isinstance(e, QueuedExecution) for e in executions)
        
        # Check first execution
        first = executions[0]
        assert first.batch_id == "batch1"
        assert first.iteration == 0
        assert first.total_iterations == 6
        assert first.x_value == "v1"
        assert first.y_value == 1
        assert first.x_index == 0
        assert first.y_index == 0
    
    def test_get_next_execution(self):
        """Test getting next execution."""
        manager = GridQueueManager()
        
        # No executions
        assert manager.get_next_execution("batch1") is None
        
        # Prepare batch
        grid_config = {
            "axes": {
                "x": {"values": ["a", "b"], "labels": []},
                "y": {"values": [1], "labels": []},
                "z": {"values": [""], "labels": []},
            },
            "dimensions": {"total_images": 2}
        }
        
        manager.prepare_batch_executions("batch1", grid_config, 1, {})
        
        # Get first execution
        execution = manager.get_next_execution("batch1")
        assert execution is not None
        assert execution.iteration == 0
        
        # Mark as complete
        manager.mark_iteration_complete("batch1", 0)
        
        # Get second execution
        execution = manager.get_next_execution("batch1")
        assert execution.iteration == 1
    
    def test_is_batch_complete(self):
        """Test batch completion checking."""
        manager = GridQueueManager()
        
        # Unknown batch is complete
        assert manager.is_batch_complete("unknown")
        
        # Prepare batch
        grid_config = {
            "axes": {
                "x": {"values": ["a"], "labels": []},
                "y": {"values": [1, 2], "labels": []},
                "z": {"values": [""], "labels": []},
            },
            "dimensions": {"total_images": 2}
        }
        
        manager.prepare_batch_executions("batch1", grid_config, 1, {})
        assert not manager.is_batch_complete("batch1")
        
        # Complete all iterations
        manager.mark_iteration_complete("batch1", 0)
        manager.mark_iteration_complete("batch1", 1)
        assert manager.is_batch_complete("batch1")
    
    def test_batch_optimization(self):
        """Test batch optimization logic."""
        manager = GridQueueManager()
        
        # Test that batch preparation preserves order
        grid_config = {
            "axes": {
                "x": {"values": ["a", "b", "a"], "labels": []},
                "y": {"values": [1], "labels": []},
                "z": {"values": [""], "labels": []},
            },
            "dimensions": {"total_images": 3}
        }
        
        executions = manager.prepare_batch_executions("batch1", grid_config, 1, {})
        
        # Check order is preserved
        assert len(executions) == 3
        assert executions[0].x_value == "a"
        assert executions[1].x_value == "b"
        assert executions[2].x_value == "a"