"""ComfyUI-specific execution flow implementation."""

import json
import uuid
from typing import Dict, List, Any, Optional, Tuple

try:
    from server import PromptServer
    from execution import validate_prompt, PromptExecutor
    import execution
    import nodes
except ImportError:
    # Not in ComfyUI environment
    PromptServer = None
    validate_prompt = None
    PromptExecutor = None
    execution = None
    nodes = None


class ComfyUIExecutionFlow:
    """Manages execution flow integration with ComfyUI's system."""
    
    _instance = None
    _batch_states = {}  # Track batch execution states
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.prompt_server = PromptServer.instance if PromptServer else None
            self.active_batches = {}
            self.execution_callbacks = {}
    
    def register_batch(self, batch_id: str, grid_config: Dict, node_id: str) -> None:
        """Register a new batch for execution tracking."""
        self._batch_states[batch_id] = {
            "config": grid_config,
            "node_id": node_id,
            "current_iteration": 0,
            "total_iterations": grid_config["total_images"],
            "completed": False
        }
    
    def queue_grid_executions(self, workflow: Dict, batch_id: str, 
                             grid_config: Dict, node_id: str) -> bool:
        """Queue all executions for a grid batch."""
        try:
            # Register the batch
            self.register_batch(batch_id, grid_config, node_id)
            
            # Get axis configurations
            x_values = grid_config["axes"]["x"]["values"]
            y_values = grid_config["axes"]["y"]["values"]
            z_values = grid_config["axes"]["z"]["values"]
            
            # Calculate total iterations
            total = len(x_values) * len(y_values) * len(z_values)
            
            # Store the original workflow
            original_workflow = json.loads(json.dumps(workflow))
            
            # Queue executions for each combination
            execution_count = 0
            for z_idx, z_val in enumerate(z_values or [""]):
                for y_idx, y_val in enumerate(y_values or [""]):
                    for x_idx, x_val in enumerate(x_values or [""]):
                        # Clone workflow for this iteration
                        iteration_workflow = json.loads(json.dumps(original_workflow))
                        
                        # Inject iteration metadata
                        self._inject_iteration_data(
                            iteration_workflow, node_id, batch_id,
                            execution_count, total,
                            x_idx, y_idx, z_idx
                        )
                        
                        # Queue this iteration
                        prompt_id = str(uuid.uuid4())
                        
                        # Use ComfyUI's internal queue system
                        if validate_prompt:
                            valid, error = validate_prompt(iteration_workflow)
                            if valid and execution and PromptServer:
                                # Add to execution queue
                                PromptServer.instance.send_sync(
                                    "execution_start", 
                                    {"prompt_id": prompt_id}
                                )
                            
                            execution_count += 1
                        else:
                            print(f"Validation error for iteration {execution_count}: {error}")
                            return False
            
            return True
            
        except Exception as e:
            print(f"Error queuing grid executions: {e}")
            return False
    
    def _inject_iteration_data(self, workflow: Dict, node_id: str, batch_id: str,
                              iteration: int, total: int, 
                              x_idx: int, y_idx: int, z_idx: int) -> None:
        """Inject iteration-specific data into workflow."""
        # Find the XYZ controller node
        if str(node_id) in workflow:
            node_data = workflow[str(node_id)]
            
            # Add hidden inputs for tracking
            if "inputs" not in node_data:
                node_data["inputs"] = {}
            
            node_data["inputs"]["_xyz_batch_id"] = batch_id
            node_data["inputs"]["_xyz_iteration"] = iteration
            node_data["inputs"]["_xyz_total"] = total
            node_data["inputs"]["_xyz_indices"] = {
                "x": x_idx,
                "y": y_idx,
                "z": z_idx
            }
    
    def get_batch_progress(self, batch_id: str) -> Dict[str, Any]:
        """Get progress information for a batch."""
        if batch_id not in self._batch_states:
            return {"status": "unknown", "progress": 0}
        
        state = self._batch_states[batch_id]
        progress = state["current_iteration"] / state["total_iterations"]
        
        return {
            "status": "completed" if state["completed"] else "running",
            "progress": progress,
            "current": state["current_iteration"],
            "total": state["total_iterations"]
        }
    
    def mark_iteration_complete(self, batch_id: str) -> None:
        """Mark current iteration as complete and advance."""
        if batch_id in self._batch_states:
            state = self._batch_states[batch_id]
            state["current_iteration"] += 1
            
            if state["current_iteration"] >= state["total_iterations"]:
                state["completed"] = True
                
                # Send completion notification
                if self.prompt_server:
                    self.prompt_server.send_sync("xyz_grid_complete", {
                        "batch_id": batch_id,
                        "total_images": state["total_iterations"]
                    })
    
    def cleanup_batch(self, batch_id: str) -> None:
        """Clean up completed batch data."""
        if batch_id in self._batch_states:
            del self._batch_states[batch_id]


# Global execution flow instance
execution_flow = ComfyUIExecutionFlow()