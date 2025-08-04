"""Tests for progress tracking."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from kikotools.tools.xyz_grid.utils.progress_tracker import (
    GridProgress, ProgressTracker
)


class TestGridProgress:
    """Test GridProgress class."""
    
    def test_initialization(self):
        """Test progress initialization."""
        progress = GridProgress(
            batch_id="test123",
            total_images=10
        )
        
        assert progress.batch_id == "test123"
        assert progress.total_images == 10
        assert progress.completed_images == 0
        assert progress.status == "initializing"
        assert progress.progress_percent == 0.0
    
    def test_progress_percent(self):
        """Test progress percentage calculation."""
        progress = GridProgress(batch_id="test", total_images=4)
        
        assert progress.progress_percent == 0.0
        
        progress.completed_images = 1
        assert progress.progress_percent == 25.0
        
        progress.completed_images = 2
        assert progress.progress_percent == 50.0
        
        progress.completed_images = 4
        assert progress.progress_percent == 100.0
    
    def test_elapsed_time(self):
        """Test elapsed time calculation."""
        # Create progress with known start time
        progress = GridProgress(batch_id="test", total_images=10)
        progress.start_time = 100.0
        
        # Mock current time for elapsed calculation
        with patch('time.time', return_value=110.5):
            assert progress.elapsed_time == 10.5
        
        # Set end time
        progress.end_time = 115.0
        assert progress.elapsed_time == 15.0
    
    def test_estimated_remaining(self):
        """Test remaining time estimation."""
        progress = GridProgress(batch_id="test", total_images=10)
        progress.start_time = 100.0
        
        # No images completed yet
        assert progress.estimated_remaining is None
        
        # Complete 2 images in 10 seconds
        progress.completed_images = 2
        
        # Mock current time for calculation
        with patch('time.time', return_value=110.0):
            # 5 seconds per image, 8 remaining = 40 seconds
            assert progress.estimated_remaining == 40.0
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        progress = GridProgress(
            batch_id="test",
            total_images=10,
            completed_images=5
        )
        progress.current_labels = {"x": "Model A", "y": "CFG 7.5"}
        
        data = progress.to_dict()
        
        assert data["batch_id"] == "test"
        assert data["total_images"] == 10
        assert data["completed_images"] == 5
        assert data["progress_percent"] == 50.0
        assert data["current_labels"] == {"x": "Model A", "y": "CFG 7.5"}
        assert data["status"] == "initializing"
        assert "elapsed_time" in data


class TestProgressTracker:
    """Test ProgressTracker class."""
    
    def test_start_grid(self):
        """Test starting a new grid."""
        tracker = ProgressTracker()
        
        progress = tracker.start_grid("batch1", 20)
        
        assert progress.batch_id == "batch1"
        assert progress.total_images == 20
        assert progress.status == "running"
        assert "batch1" in tracker.active_grids
    
    def test_update_progress(self):
        """Test updating progress."""
        tracker = ProgressTracker()
        tracker.start_grid("batch1", 5)
        
        # Update with increment
        progress = tracker.update_progress("batch1")
        assert progress.completed_images == 1
        
        # Update with specific count
        progress = tracker.update_progress("batch1", completed=3)
        assert progress.completed_images == 3
        
        # Update with labels
        labels = {"x": "Model B", "y": "Steps 30"}
        progress = tracker.update_progress("batch1", current_labels=labels)
        assert progress.current_labels == labels
    
    def test_update_with_preview(self):
        """Test updating with preview images."""
        tracker = ProgressTracker()
        tracker.start_grid("batch1", 10)
        
        # Add previews
        for i in range(7):
            tracker.update_progress("batch1", preview_image=f"image_{i}")
        
        progress = tracker.get_progress("batch1")
        # Should only keep last 5
        assert len(progress.preview_images) == 5
        assert progress.preview_images[-1] == "image_6"
    
    def test_complete_grid(self):
        """Test completing a grid."""
        tracker = ProgressTracker()
        tracker.start_grid("batch1", 2)
        
        # Complete all images
        tracker.update_progress("batch1", completed=2)
        
        # Should auto-complete
        assert "batch1" not in tracker.active_grids
        assert len(tracker.completed_grids) == 1
        
        completed = tracker.completed_grids[0]
        assert completed.status == "completed"
        assert completed.end_time is not None
    
    def test_error_grid(self):
        """Test error handling."""
        tracker = ProgressTracker()
        tracker.start_grid("batch1", 10)
        
        progress = tracker.error_grid("batch1", "CUDA out of memory")
        
        assert progress.status == "error"
        assert progress.error_message == "CUDA out of memory"
        assert "batch1" not in tracker.active_grids
        assert len(tracker.completed_grids) == 1
    
    def test_get_progress(self):
        """Test getting progress for specific batch."""
        tracker = ProgressTracker()
        
        # Non-existent batch
        assert tracker.get_progress("unknown") is None
        
        # Active batch
        tracker.start_grid("batch1", 10)
        progress = tracker.get_progress("batch1")
        assert progress is not None
        assert progress.batch_id == "batch1"
        
        # Completed batch
        tracker.complete_grid("batch1")
        progress = tracker.get_progress("batch1")
        assert progress is not None
        assert progress.status == "completed"
    
    def test_callbacks(self):
        """Test progress callbacks."""
        tracker = ProgressTracker()
        
        callback_data = []
        def test_callback(progress):
            callback_data.append(progress.to_dict())
        
        tracker.register_callback(test_callback)
        
        # Start should trigger callback
        tracker.start_grid("batch1", 5)
        assert len(callback_data) == 1
        assert callback_data[0]["batch_id"] == "batch1"
        
        # Update should trigger callback
        tracker.update_progress("batch1")
        assert len(callback_data) == 2
        assert callback_data[1]["completed_images"] == 1
    
    def test_websocket_notification(self):
        """Test WebSocket notifications."""
        tracker = ProgressTracker()
        
        # Test with mock websocket handler
        mock_handler = Mock()
        tracker.set_websocket_handler(mock_handler)
        
        # Test callback gets called
        callback_called = False
        def test_callback(progress):
            nonlocal callback_called
            callback_called = True
        
        tracker.register_callback(test_callback)
        tracker.start_grid("batch1", 10)
        
        assert callback_called
    
    def test_get_summary(self):
        """Test getting progress summary."""
        tracker = ProgressTracker()
        
        # Add some grids
        tracker.start_grid("batch1", 10)
        tracker.start_grid("batch2", 20)
        
        # Complete one
        tracker.complete_grid("batch1")
        
        summary = tracker.get_summary()
        
        assert summary["total_active"] == 1
        assert summary["total_completed"] == 1
        assert len(summary["active_grids"]) == 1
        assert len(summary["completed_grids"]) == 1
        assert summary["active_grids"][0]["batch_id"] == "batch2"
    
    def test_completed_grids_limit(self):
        """Test that completed grids list has a limit."""
        tracker = ProgressTracker()
        
        # Complete many grids
        for i in range(15):
            tracker.start_grid(f"batch{i}", 5)
            tracker.complete_grid(f"batch{i}")
        
        # Should only keep last 10
        assert len(tracker.completed_grids) == 10
        
        # Check it's the most recent ones
        last_batch_id = tracker.completed_grids[-1].batch_id
        assert last_batch_id == "batch14"