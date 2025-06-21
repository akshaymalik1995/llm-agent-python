import json
from src.custom_logging import logger

class PlanValidator:
    """Validates execution plan structure and dependencies."""

    @staticmethod
    def validate_plan_structure(plan_data: dict) -> bool:
        """Validate the structure of the recieved plan."""
        if not isinstance(plan_data, dict):
            logger.error("Plan data is not a dictionary")
            return False
        
        if "plan" not in plan_data or not isinstance(plan_data['plan'], list):
            logger.error("Plan data missing 'plan' field or not a list")
            return False
        
        if not plan_data['plan']:
            logger.error("Plan is empty")
            return False
        
        # Validate each step
        for step in plan_data['plan']:
            if not PlanValidator._validate_step(step):
                return False
        return True
    
    # TODO: Perhaps have a data class for Step
    # TODO: Perhaps use pydantic to validate
    @staticmethod
    def _validate_step(step: dict) -> bool:
        """Validate individual step structure"""
        if not isinstance(step, dict) or "id" not in step or "type" not in step:
            logger.error(f"Invalid step structure: {step}")
            return False
        
        # Validate conditional steps
        # TODO: Requires more logic 
        if step.get("type") == "if":
            condition = step.get("condition", "")
            operators = [" == ", " != ", " >= ", " <= ", " > ", " < "]
            if not any(op in condition for op in operators):
                logger.error(f"Invalid condition format in step {step.get('id')}: {condition}")
                return False
            
        return True
    
    @staticmethod
    def validate_dependencies(plan_data: dict) -> bool:
        """Validates that all input_refs reference valid output_names."""
        steps = plan_data.get('plan', [])
        available_outputs = set()

        for step in steps:
            # Check if input_refs reference available outputs
            input_refs = step.get("input_refs", [])
            for ref in input_refs:
                if ref not in available_outputs:
                    logger.warning(f"Step {step.get("id")} references undefined output: {ref}")
                    return False
            # Add this step's output to available outputs
            if step.get("output_name"):
                available_outputs.add(step['output_name'])
        return True
    
    @staticmethod
    def _validate_response_format(step: dict) -> bool:
        pass # TODO:
