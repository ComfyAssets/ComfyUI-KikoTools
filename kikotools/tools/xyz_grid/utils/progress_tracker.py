"""Progress tracking and preview capabilities for XYZ grids."""

import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio


@dataclass
class GridProgress:
    """Tracks progress for a single grid generation."""
    batch_id: str
    total_images: int
    completed_images: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    current_labels: Dict[str, str] = field(default_factory=dict)
    preview_images: List[Any] = field(default_factory=list)
    status: str = "initializing"  # initializing, running, completed, error
    error_message: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        if self.total_images == 0:
            return 0.0
        return (self.completed_images / self.total_images) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def estimated_remaining(self) -> Optional[float]:
        """Estimate remaining time in seconds."""
        if self.completed_images == 0:
            return None
        
        avg_time_per_image = self.elapsed_time / self.completed_images
        remaining_images = self.total_images - self.completed_images
        return avg_time_per_image * remaining_images
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "batch_id": self.batch_id,
            "total_images": self.total_images,
            "completed_images": self.completed_images,
            "progress_percent": round(self.progress_percent, 1),
            "elapsed_time": round(self.elapsed_time, 1),
            "estimated_remaining": round(self.estimated_remaining, 1) if self.estimated_remaining else None,
            "current_labels": self.current_labels,
            "status": self.status,
            "error_message": self.error_message,
            "preview_count": len(self.preview_images)
        }


class ProgressTracker:
    """Manages progress tracking for all grid generations."""
    
    def __init__(self):
        self.active_grids: Dict[str, GridProgress] = {}
        self.completed_grids: List[GridProgress] = []
        self.progress_callbacks: List[Callable] = []
        self.websocket_handler = None
    
    def start_grid(self, batch_id: str, total_images: int) -> GridProgress:
        """Start tracking a new grid generation."""
        progress = GridProgress(
            batch_id=batch_id,
            total_images=total_images,
            status="running"
        )
        self.active_grids[batch_id] = progress
        self._notify_progress(progress)
        return progress
    
    def update_progress(self, batch_id: str, completed: int = None,
                       current_labels: Dict[str, str] = None,
                       preview_image: Any = None) -> Optional[GridProgress]:
        """Update progress for a grid."""
        if batch_id not in self.active_grids:
            return None
        
        progress = self.active_grids[batch_id]
        
        if completed is not None:
            progress.completed_images = completed
        else:
            progress.completed_images += 1
        
        if current_labels:
            progress.current_labels = current_labels
        
        if preview_image is not None:
            progress.preview_images.append(preview_image)
            # Keep only last N previews to save memory
            if len(progress.preview_images) > 5:
                progress.preview_images.pop(0)
        
        self._notify_progress(progress)
        
        # Check if completed
        if progress.completed_images >= progress.total_images:
            self.complete_grid(batch_id)
        
        return progress
    
    def complete_grid(self, batch_id: str) -> Optional[GridProgress]:
        """Mark a grid as completed."""
        if batch_id not in self.active_grids:
            return None
        
        progress = self.active_grids[batch_id]
        progress.status = "completed"
        progress.end_time = time.time()
        
        # Move to completed list
        self.completed_grids.append(progress)
        del self.active_grids[batch_id]
        
        # Keep only last N completed grids
        if len(self.completed_grids) > 10:
            self.completed_grids.pop(0)
        
        self._notify_progress(progress)
        return progress
    
    def error_grid(self, batch_id: str, error_message: str) -> Optional[GridProgress]:
        """Mark a grid as errored."""
        if batch_id not in self.active_grids:
            return None
        
        progress = self.active_grids[batch_id]
        progress.status = "error"
        progress.error_message = error_message
        progress.end_time = time.time()
        
        # Move to completed list (with error status)
        self.completed_grids.append(progress)
        del self.active_grids[batch_id]
        
        self._notify_progress(progress)
        return progress
    
    def get_progress(self, batch_id: str) -> Optional[GridProgress]:
        """Get progress for a specific grid."""
        if batch_id in self.active_grids:
            return self.active_grids[batch_id]
        
        # Check completed grids
        for grid in self.completed_grids:
            if grid.batch_id == batch_id:
                return grid
        
        return None
    
    def get_all_active(self) -> List[GridProgress]:
        """Get all active grid progress."""
        return list(self.active_grids.values())
    
    def register_callback(self, callback: Callable[[GridProgress], None]) -> None:
        """Register a progress callback."""
        self.progress_callbacks.append(callback)
    
    def set_websocket_handler(self, handler: Any) -> None:
        """Set WebSocket handler for real-time updates."""
        self.websocket_handler = handler
    
    def _notify_progress(self, progress: GridProgress) -> None:
        """Notify all registered callbacks of progress update."""
        # Call registered callbacks
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                print(f"Error in progress callback: {e}")
        
        # Send WebSocket update if available
        if self.websocket_handler:
            try:
                self._send_websocket_update(progress)
            except Exception as e:
                print(f"Error sending WebSocket update: {e}")
    
    def _send_websocket_update(self, progress: GridProgress) -> None:
        """Send progress update via WebSocket."""
        if not self.websocket_handler:
            return
        
        message = {
            "type": "xyz_grid_progress",
            "data": progress.to_dict()
        }
        
        # This would integrate with ComfyUI's server
        try:
            from server import PromptServer
            if PromptServer:
                server = PromptServer.instance
                if server:
                    server.send_sync("xyz_grid_progress", message["data"])
        except:
            pass
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all progress."""
        return {
            "active_grids": [p.to_dict() for p in self.active_grids.values()],
            "completed_grids": [p.to_dict() for p in self.completed_grids[-5:]],  # Last 5
            "total_active": len(self.active_grids),
            "total_completed": len(self.completed_grids)
        }


# Global progress tracker instance
progress_tracker = ProgressTracker()


class ProgressWebSocketHandler:
    """WebSocket handler for progress updates."""
    
    def __init__(self):
        self.clients = set()
    
    async def handle_client(self, websocket, path):
        """Handle a WebSocket client connection."""
        self.clients.add(websocket)
        try:
            # Send initial state
            summary = progress_tracker.get_summary()
            await websocket.send(json.dumps({
                "type": "xyz_grid_init",
                "data": summary
            }))
            
            # Keep connection alive
            async for message in websocket:
                # Handle any client messages if needed
                pass
        finally:
            self.clients.remove(websocket)
    
    async def broadcast_progress(self, progress: GridProgress):
        """Broadcast progress to all connected clients."""
        if self.clients:
            message = json.dumps({
                "type": "xyz_grid_progress",
                "data": progress.to_dict()
            })
            # Send to all connected clients
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(message)
                except:
                    disconnected.add(client)
            
            # Remove disconnected clients
            self.clients -= disconnected