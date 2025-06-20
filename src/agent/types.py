from typing import Literal, Optional, Union
from dataclasses import dataclass

@dataclass
class PlanStep:
    id: str
    type: Literal["llm", "tool", 'if', "goto", "end"]

    description: Optional[str] = None

    # For LLM Steps
    prompt: Optional[str] = None
    response_format: Optional[dict] = None  # ← ADD THIS LINE

    # For tool steps
    tool_name: Optional[str] = None
    arguments: Optional[dict] = None

    # For control flow
    condition: Optional[str] = None # For "if" type
    goto_id: Optional[str] = None # For "goto" type

    # Input/output tracking
    input_refs: Optional[list[str]] = None # References to previous outputs
    output_name: Optional[str] = None # Name for this step's output

    # Execution tracking
    executed: bool = False
    result: Optional[str] = None


@dataclass
class ExecutionPlan:
    steps: list[PlanStep]
    max_iterations: int
    reasoning: str
    current_step_index: int = 0
    outputs: Optional[dict[str: str]] = None # Maps output_name -> actual result
    

    def __post_init__(self):
        if self.outputs is None:
            self.outputs = {}


