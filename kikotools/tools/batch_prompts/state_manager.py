"""State management for batch prompts using file persistence."""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any


class StateManager:
    """Manages persistent state for batch prompt execution."""

    def __init__(self):
        # Use temp directory for state files
        self.state_dir = Path(tempfile.gettempdir()) / "comfyui_batch_prompts"
        self.state_dir.mkdir(exist_ok=True)
        self.state_file = self.state_dir / "execution_state.json"

    def get_state(self) -> Dict[str, Any]:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_state(self, state: Dict[str, Any]):
        """Save state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"[BatchPrompts] Failed to save state: {e}")

    def get_execution_count(self, file_path: str) -> int:
        """Get execution count for a specific file."""
        state = self.get_state()
        counts = state.get("execution_counts", {})
        return counts.get(file_path, 0)

    def increment_execution_count(self, file_path: str) -> int:
        """Increment and return execution count for a file."""
        state = self.get_state()
        counts = state.get("execution_counts", {})
        current = counts.get(file_path, 0)
        counts[file_path] = current + 1
        state["execution_counts"] = counts
        self.save_state(state)
        return current

    def reset_execution_count(self, file_path: str):
        """Reset execution count for a file."""
        state = self.get_state()
        counts = state.get("execution_counts", {})
        counts[file_path] = 0
        state["execution_counts"] = counts
        self.save_state(state)


# Global state manager instance
STATE_MANAGER = StateManager()
