"""Execution flow management for XYZ grid generation."""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from ..utils.constants import AxisType


@dataclass
class GridExecutionState:
    """Tracks execution state for grid generation."""
    batch_id: str
    total_iterations: int
    current_iteration: int = 0
    x_index: int = 0
    y_index: int = 0
    z_index: int = 0
    x_count: int = 1
    y_count: int = 1
    z_count: int = 1
    
    def advance(self) -> bool:
        """Advance to next grid position. Returns False when complete."""
        self.current_iteration += 1
        
        if self.current_iteration >= self.total_iterations:
            return False
        
        # Advance indices (row-major order: X varies fastest)
        self.x_index += 1
        if self.x_index >= self.x_count:
            self.x_index = 0
            self.y_index += 1
            if self.y_index >= self.y_count:
                self.y_index = 0
                self.z_index += 1
        
        return True
    
    def get_indices(self) -> Tuple[int, int, int]:
        """Get current x, y, z indices."""
        return (self.x_index, self.y_index, self.z_index)
    
    def is_complete(self) -> bool:
        """Check if all iterations are complete."""
        return self.current_iteration >= self.total_iterations


class ExecutionManager:
    """Manages execution flow for XYZ grid generation."""
    
    def __init__(self):
        self.execution_states = {}  # batch_id -> GridExecutionState
        self.pending_executions = {}  # batch_id -> list of pending configs
    
    def initialize_batch(self, batch_id: str, x_values: List[Any], 
                        y_values: List[Any], z_values: List[Any]) -> GridExecutionState:
        """Initialize a new batch execution."""
        x_count = len(x_values) if x_values else 1
        y_count = len(y_values) if y_values else 1
        z_count = len(z_values) if z_values else 1
        total = x_count * y_count * z_count
        
        state = GridExecutionState(
            batch_id=batch_id,
            total_iterations=total,
            x_count=x_count,
            y_count=y_count,
            z_count=z_count
        )
        
        self.execution_states[batch_id] = state
        return state
    
    def get_current_values(self, batch_id: str, x_values: List[Any],
                          y_values: List[Any], z_values: List[Any]) -> Tuple[Any, Any, Any, int, int, int]:
        """Get current values and indices for execution."""
        state = self.execution_states.get(batch_id)
        if not state:
            # Initialize if not exists
            state = self.initialize_batch(batch_id, x_values, y_values, z_values)
        
        x_idx, y_idx, z_idx = state.get_indices()
        
        x_val = x_values[x_idx] if x_values and x_idx < len(x_values) else ""
        y_val = y_values[y_idx] if y_values and y_idx < len(y_values) else ""
        z_val = z_values[z_idx] if z_values and z_idx < len(z_values) else ""
        
        return x_val, y_val, z_val, x_idx, y_idx, z_idx
    
    def should_continue(self, batch_id: str) -> bool:
        """Check if batch should continue executing."""
        state = self.execution_states.get(batch_id)
        return state and not state.is_complete()
    
    def advance_batch(self, batch_id: str) -> bool:
        """Advance to next iteration. Returns True if more iterations remain."""
        state = self.execution_states.get(batch_id)
        if state:
            return state.advance()
        return False
    
    def cleanup_batch(self, batch_id: str):
        """Clean up completed batch."""
        if batch_id in self.execution_states:
            del self.execution_states[batch_id]
        if batch_id in self.pending_executions:
            del self.pending_executions[batch_id]


# Global execution manager instance
execution_manager = ExecutionManager()