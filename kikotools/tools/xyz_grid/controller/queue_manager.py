"""Queue management for automated grid execution."""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import uuid
import json


@dataclass
class QueuedExecution:
    """Represents a queued execution for grid generation."""
    execution_id: str
    batch_id: str
    iteration: int
    total_iterations: int
    x_value: Any
    y_value: Any
    z_value: Any
    x_index: int
    y_index: int
    z_index: int
    workflow_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "batch_id": self.batch_id,
            "iteration": self.iteration,
            "total_iterations": self.total_iterations,
            "indices": {
                "x": self.x_index,
                "y": self.y_index,
                "z": self.z_index
            },
            "values": {
                "x": self.x_value,
                "y": self.y_value,
                "z": self.z_value
            }
        }


class GridQueueManager:
    """Manages the execution queue for grid generation."""
    
    def __init__(self):
        self.execution_queue: Dict[str, List[QueuedExecution]] = {}  # batch_id -> executions
        self.active_batches: Dict[str, Dict] = {}  # batch_id -> batch info
        self.completed_iterations: Dict[str, List[int]] = {}  # batch_id -> completed iteration indices
        
    def prepare_batch_executions(self, batch_id: str, grid_config: Dict, 
                               node_id: int, workflow: Dict) -> List[QueuedExecution]:
        """Prepare all executions for a batch."""
        executions = []
        
        x_values = grid_config["axes"]["x"]["values"]
        y_values = grid_config["axes"]["y"]["values"]
        z_values = grid_config["axes"]["z"]["values"]
        
        total_iterations = len(x_values) * len(y_values) * len(z_values)
        iteration = 0
        
        # Generate all combinations
        for z_idx, z_val in enumerate(z_values or [""]):
            for y_idx, y_val in enumerate(y_values or [""]):
                for x_idx, x_val in enumerate(x_values or [""]):
                    execution = QueuedExecution(
                        execution_id=str(uuid.uuid4()),
                        batch_id=batch_id,
                        iteration=iteration,
                        total_iterations=total_iterations,
                        x_value=x_val,
                        y_value=y_val,
                        z_value=z_val,
                        x_index=x_idx,
                        y_index=y_idx,
                        z_index=z_idx,
                        workflow_data=self._prepare_workflow(workflow, node_id, grid_config)
                    )
                    executions.append(execution)
                    iteration += 1
        
        # Store batch info
        self.execution_queue[batch_id] = executions
        self.active_batches[batch_id] = {
            "total_iterations": total_iterations,
            "grid_config": grid_config,
            "node_id": node_id
        }
        self.completed_iterations[batch_id] = []
        
        return executions
    
    def get_next_execution(self, batch_id: str) -> Optional[QueuedExecution]:
        """Get the next execution for a batch."""
        if batch_id not in self.execution_queue:
            return None
        
        executions = self.execution_queue[batch_id]
        completed = self.completed_iterations.get(batch_id, [])
        
        # Find next uncompleted execution
        for execution in executions:
            if execution.iteration not in completed:
                return execution
        
        return None
    
    def mark_iteration_complete(self, batch_id: str, iteration: int):
        """Mark an iteration as complete."""
        if batch_id not in self.completed_iterations:
            self.completed_iterations[batch_id] = []
        
        if iteration not in self.completed_iterations[batch_id]:
            self.completed_iterations[batch_id].append(iteration)
    
    def is_batch_complete(self, batch_id: str) -> bool:
        """Check if all iterations for a batch are complete."""
        if batch_id not in self.active_batches:
            return True
        
        total = self.active_batches[batch_id]["total_iterations"]
        completed = len(self.completed_iterations.get(batch_id, []))
        
        return completed >= total
    
    def cleanup_batch(self, batch_id: str):
        """Clean up a completed batch."""
        if batch_id in self.execution_queue:
            del self.execution_queue[batch_id]
        if batch_id in self.active_batches:
            del self.active_batches[batch_id]
        if batch_id in self.completed_iterations:
            del self.completed_iterations[batch_id]
    
    def _prepare_workflow(self, base_workflow: Dict, node_id: int, grid_config: Dict) -> Dict:
        """Prepare workflow data for execution."""
        # This would modify the workflow to set appropriate values
        # For now, return a copy of the base workflow
        import copy
        return copy.deepcopy(base_workflow)
    
    async def execute_batch_async(self, batch_id: str, api_client: Any):
        """Execute all iterations for a batch asynchronously."""
        executions = self.execution_queue.get(batch_id, [])
        
        for execution in executions:
            if execution.iteration in self.completed_iterations.get(batch_id, []):
                continue
            
            # Queue the execution via ComfyUI API
            try:
                # This would use the actual ComfyUI API client
                # await api_client.queue_prompt(execution.workflow_data)
                pass
            except Exception as e:
                print(f"Error queuing execution {execution.execution_id}: {e}")
            
            # Small delay between queuing to avoid overwhelming the system
            await asyncio.sleep(0.1)


# Global queue manager instance
queue_manager = GridQueueManager()