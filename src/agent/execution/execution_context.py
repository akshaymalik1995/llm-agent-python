from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Callable
from src.agent.types import ExecutionPlan

@dataclass
class ExecutionContext:
    """Manages execution state and context."""

    plan: ExecutionPlan
    current_step_index: int = 0
    outputs: Dict[str, str] = field(default_factory=dict)
    jumped: bool = False
    step_callback: Optional[Callable] = None

    def get_current_step(self):
        """Get the current step being executed."""
        if self.current_step_index < len(self.plan.steps):
            return self.plan.steps[self.current_step_index]
        return None
    
    