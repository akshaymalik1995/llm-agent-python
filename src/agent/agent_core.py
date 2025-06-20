from src.tooling.tool_registry import ToolRegistry
import json
from src.llm_interface.base_llm_interface import BaseLLMInterface
from src.config import settings
from src.agent.types import PlanStep, ExecutionPlan
from src.prompts.planning_prompt import PLANNING_PROMPT
from typing import Optional, Any
from src.custom_logging import logger
import tiktoken
import enum
from src.tooling.tool_selectors import KeywordToolSelector
from datetime import datetime

class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageDict:
    def __init__(self, role: MessageRole, content: str):
        self.role = role
        self.content = content

class AgentCore:
    def __init__(self, llm_interface: BaseLLMInterface, tool_registry: ToolRegistry, step_callback=None):
        """
        Initializes the AI Agent with planning-based execution.

        Args:
            llm_interface: An object responsible for interacting with the LLM.
            tool_registry: An instance of ToolRegistry containing available tools.
            step_callback: Optional callback function for step execution updates.
                          Should accept (step_id, event_type, data) parameters.
        """
        self.llm_interface = llm_interface
        self.tool_registry = tool_registry
        self.conversation_history: list[MessageDict] = []

        # Token Management
        self.max_tokens = 25000
        self.token_buffer = 2000
        self.effective_max_tokens = self.max_tokens - self.token_buffer
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

        # Execution state
        self.current_plan: Optional[ExecutionPlan] = None
        self.jumped = False # Flag for tracking jumps in plan execution
        self.step_callback = step_callback  # Add this line

    def execute_task(self, user_query:str, max_iterations: Optional[int] = None) -> str:
        """
        Main entry point for task execution using planning-based approach.
        
        Args:
            user_query: The user's task request
            max_iterations: Override for maximum iterations (uses plan estimate if None)
            
        Returns:
            Final result or error message
        """
        try:
            # Phase 1: Create execution plan
            logger.info(f"Starting task: {user_query}")
            self._add_to_history(MessageRole.USER.value, user_query)

            plan_data = self._create_execution_plan(user_query)

            if not plan_data:
                return "Error: Failed to create execution plan"
            
            # Phase 2: Execute the plan
            result = self._execute_plan(plan_data, max_iterations)
            return result

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return f"Error during task execution: {str(e)}"
        
    def _create_execution_plan(self, user_query: str) -> Optional[dict]:
        """
        Creates an execution plan by calling the LLM with planning prompt.
        
        Returns:
            Parsed plan data or None if planning failed
        """

        logger.info("Creating execution plan...")

        # Select relevant tools instead of using all tools
        tool_selector = KeywordToolSelector(self.tool_registry)
        relevant_tools = tool_selector.select_relevant_tools(user_query, max_tools=4)
        
        logger.info(f"Selected tools: {relevant_tools}")
        print(f"Selected tools: {relevant_tools}")

        # Format planning prompt with available tools
        tool_schemas_json = json.dumps(self.tool_registry.get_all_tools_info(relevant_tools), indent=2)
        planning_prompt = PLANNING_PROMPT.replace("{tools_schemas_json}", tool_schemas_json)



        # Construct planning messages
        messages = [
            {"role": MessageRole.SYSTEM.value, "content": planning_prompt},
            {"role": "user", "content": f"Create an execution plan for: {user_query}"}
        ]

        try:
            # get plan from LLM
            response = self.llm_interface.get_completion(messages=messages, force_json=True)
            logger.info(f"Planning response received: {response}")
            print(f"Planning response received: {response}")

            # Parse the plan
            plan_data = json.loads(response.strip())

            # Validate plan structure
            if not self._validate_plan_structure(plan_data):
                logger.error("Invalid plan structure received")
                return None
            
            logger.info(f"Plan created successfully with {len(plan_data['plan'])} steps")
            return plan_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse planning response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return None
        
    def _validate_plan_structure(self, plan_data: dict) -> bool:
        """Validates the structure of the received plan."""
        if not isinstance(plan_data, dict):
            return False
        
        if "plan" not in plan_data or not isinstance(plan_data['plan'], list):
            return False
        
        # Check that plan has at least one step and ends with "end"
        if not plan_data['plan']:
            return False

        # Validate each step has required fields
        for step in plan_data["plan"]:
            if not isinstance(step, dict) or "id" not in step or "type" not in step:
                return False
            
            # In _validate_plan_structure method, add validation for conditional steps:
            if step.get("type") == "if":
                condition = step.get("condition", "")
                if " == 'true'" not in condition:
                    logger.error(f"Invalid condition format in step {step.get('id')}: {condition}")
                    return False

        # TODO: Validate all input_refs are actually correct

        return True
    
    def _execute_plan(self, plan_data: dict, max_iterations: Optional[int] = None) -> str:
        """
        Executes the created plan step by step.
        
        Args:
            plan_data: The plan dictionary from planning phase
            max_iterations: Override for maximum iterations
            
        Returns:
            Final execution result
        """

        # Create Execution Plan Object
        steps = [PlanStep(**step_dict) for step_dict in plan_data['plan']]

        self.current_plan = ExecutionPlan(
            steps=steps,
            max_iterations = plan_data.get("max_iterations"),
            reasoning=plan_data.get("reasoning")
        )

        # Determine iteration limit
        if max_iterations is None:
            max_iterations = self.current_plan.max_iterations or settings.MAX_AGENT_ITERATIONS

        logger.info(f"Executing plan with {len(steps)} steps, max iterations: {max_iterations}")

        current_iteration = 0

        while current_iteration < max_iterations:
            current_iteration += 1

            # Check if we have reached the end
            if self.current_plan.current_step_index >= len(self.current_plan.steps):
                logger.info("Reached end of plan")
                break

            current_step = self.current_plan.steps[self.current_plan.current_step_index]

            # Skip already executed steps (for jump scenarios)
            # TODO: Understand this better later
            if current_step.executed and current_step.type not in ["if", "goto"]:
                self.current_plan.current_step_index += 1
                continue

            logger.info(f"Iteration {current_iteration}: Executing step {current_step.id} ({current_step.type})")
            print(f"Iteration {current_iteration}: Executing step {current_step.id} ({current_step.type})")

            # Execute the current step
            success = self._execute_step(current_step)

            if not success:
                error_msg = f"Failed to execute step {current_step.id}"
                logger.error(error_msg)
                return error_msg

            # Handle end step
            if current_step.type == "end":
                logger.info("Execution completed successfully")
                break

            # Move to next step (unless we jumped)
            if not self.jumped:
                self.current_plan.current_step_index += 1
            else:
                self.jumped = False

        # Return final result
        return self._get_final_result()
    
    def _execute_step(self, step: PlanStep) -> bool:
        """
        Executes a single plan step.
        
        Args:
            step: The PlanStep to execute
            
        Returns:
            True if successful, False otherwise
        """

        # Notify callback that step is starting
        self._notify_callback(step.id, 'started', {
            'step_type': step.type,
            'description': step.description
        })

        try:
            if step.type == "llm":
                success = self._execute_llm_step(step)
            elif step.type == "tool":
                success = self._execute_tool_step(step)
            elif step.type == "if":
                success = self._execute_if_step(step)
            elif step.type == "goto":
                success = self._execute_goto_step(step)
            elif step.type == "end":
                step.executed = True
                success = True
            else:
                logger.error(f"Unknown step type: {step.type}")
                success = False
            
            # Notify callback of completion
            event_type = 'completed' if success else 'failed'
            self._notify_callback(step.id, event_type, {
                'success': success,
                'result': getattr(step, 'result', None),
                'executed': getattr(step, 'executed', False)
            })
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing step {step.id}: {e}")
            
            # Notify callback of failure
            self._notify_callback(step.id, 'failed', {
                'success': False,
                'error': str(e)
            })
            
            return False
        
    def _execute_llm_step(self, step: PlanStep) -> bool:
        """Executes an LLM step."""
        if not step.prompt:
            logger.error(f"LLM step {step.id} missing prompt")
            return False
        
        # Resolve input references in the prompt
        resolved_prompt = self._resolve_prompt_inputs(step.prompt, step.input_refs)

        logger.info(f"\n\n\n\nLLM call for step {step.id}: {resolved_prompt}\n\n\n")

        # Make LLM call
        messages = [
            {"role": "system", "content" : settings.DEFAULT_SYSTEM_PROMPT_TEMPLATE},
            {"role": "user", "content": resolved_prompt}
        ]
        response = self.llm_interface.get_completion(messages=messages)


        if not response:
            logger.error(f"Empty response from LLM for step {step.id}")
            return False
        
        # Store result
        step.result = response
        step.executed = True

        # Store in outputs if output_name is specified
        if step.output_name:
            self.current_plan.outputs[step.output_name] = response
            logger.info(f"Stored output '{step.output_name}': {response[:100]}...")

        # Add to conversation history
        self._add_to_history(MessageRole.ASSISTANT, f"Step {step.id}: {response}")

        return True
    
    def _execute_tool_step(self, step: PlanStep) -> bool:
        """Executes a tool step."""
        if not step.tool_name:
            logger.error(f"Tool step {step.id} missing tool_name")
            return False
        
        tool = self.tool_registry.get_tool(step.tool_name)
        if not tool:
            logger.error(f"Unknown tool: {step.tool_name}")
            return False
        
        # Resolve arguments if they reference previous outputs
        resolved_args = self._resolve_tool_arguments(step.arguments, step.input_refs)

        logger.info(f"Tool call for step {step.id}: {step.tool_name} with args {resolved_args}")

        # Execute tool
        result = tool.execute(resolved_args or {})

        # Store result
        step.result = str(result)
        step.executed = True
        
        # Store in outputs if output_name is specified
        if step.output_name:
            self.current_plan.outputs[step.output_name] = step.result
            logger.info(f"Stored output '{step.output_name}': {step.result[:100]}...")
        
        # Add to conversation history
        self._add_to_history(MessageRole.ASSISTANT, f"Step {step.id} - Tool {step.tool_name}: {step.result}")
        
        return True
    
    def _execute_if_step(self, step: PlanStep) -> bool:
        """Executes a conditional step."""
        if not step.condition:
            logger.error(f"If step {step.id} missing condition")
            return False
        
        # Evaluate condition
        condition_result = self._evaluate_condition(step.condition)

        logger.info(f"Condition '{step.condition}' evaluated to: {condition_result}")

        # Jump if condition is true
        if condition_result and step.goto_id:
            self._jump_to_step(step.goto_id)

        step.executed = True
        return True
    
    def _execute_goto_step(self, step: PlanStep) -> bool:
        """Executes a goto step."""
        if not step.goto_id:
            logger.error(f"Goto step {step.id} missing goto_id")
            return False
        
        self._jump_to_step(step.goto_id)
        step.executed = True
        return True
    
    def _resolve_prompt_inputs(self, prompt: str, input_refs: Optional[list[str]]) -> str:
        """
        Resolves input references in a prompt string.
        
        Args:
            prompt: The prompt template with {variable} placeholders
            input_refs: List of output names to reference
            
        Returns:
            Resolved prompt string
        """

        if not input_refs:
            return prompt
        
        resolved_prompt = prompt

        # Replace each {variable} with its value from outputs
        for ref in input_refs:
            if ref in self.current_plan.outputs:
                # TODO: Check if placeholder implementation is correct
                placeholder = f"{{{ref}}}"
                value = self.current_plan.outputs[ref]
                resolved_prompt = resolved_prompt.replace(placeholder, value)
            else:
                logger.warning(f"Referenced output '{ref}' not found in outputs")
        
        return resolved_prompt
    
    def _resolve_tool_arguments(self, arguments: Optional[dict], input_refs: Optional[list[str]]) -> Optional[dict]:
        """
        Resolves input references in tool arguments.
        
        Args:
            arguments: The tool arguments dictionary
            input_refs: List of output names that might be referenced
            
        Returns:
            Resolved arguments dictionary
        """

        if not arguments:
            return arguments
        
        if not input_refs:
            return arguments
        
        # For now, simple approach - could be enhanced for complex argument resolution
        resolved_args = arguments.copy()

        # If arguments contain string references to outputs, replace them
        for key, value in resolved_args.items():
            if isinstance(value, str):
                # Handle both direct references and template-style references
                if value in self.current_plan.outputs:
                    resolved_args[key] = self.current_plan.outputs[value]
                else:
                    # Handle {variable_name} style references
                    for ref in input_refs or []:
                        if ref in self.current_plan.outputs:
                            placeholder = f"{{{ref}}}"
                            if placeholder in value:
                                resolved_args[key] = value.replace(placeholder, self.current_plan.outputs[ref])
        
        return resolved_args
    
    def _evaluate_condition(self, condition: str) -> bool:
        """
        Evaluates a condition string against current outputs.
        Only supports: variable_name == 'true'
        
        Args:
            condition: Condition string like "is_ready == 'true'"
            
        Returns:
            Boolean result of condition evaluation
        """

        try:
            # Parse condition - should be in format: variable_name == 'true'
            if " == 'true'" not in condition:
                logger.error(f"Invalid condition format: {condition}. Must be 'variable_name == \"true\"'")
                return False
                
            variable_name = condition.replace(" == 'true'", "").strip()
            
            # Check if variable exists in outputs
            if variable_name not in self.current_plan.outputs:
                logger.error(f"Variable '{variable_name}' not found in outputs")
                return False
                
            # Get the value and check if it's "true"
            output_value = self.current_plan.outputs[variable_name].strip().lower()
            result = output_value == 'true'
            
            logger.info(f"Condition '{condition}' evaluated to: {result} (variable value: '{output_value}')")
            return result
        
        except Exception as e:
            logger.error(f"Failed to evaluate condition '{condition}': {e}")
            return False
        
    def _jump_to_step(self, target_id: str) -> bool:
        """
        Jumps to a step with the given ID.
        
        Args:
            target_id: The ID of the step to jump to
            
        Returns:
            True if jump was successful, False otherwise
        """
        for i, step in enumerate(self.current_plan.steps):
            if step.id == target_id:
                self.current_plan.current_step_index = i
                self.jumped = True
                logger.info(f"Jumped to step {target_id} (index {i})")
                return True
            
        logger.error(f"Jump target '{target_id}' not found")
        return False
    
    def _get_final_result(self) -> str:
        """
        Determines the final result from plan execution.
        
        Returns:
            Final result string
        """

        outputs = self.current_plan.outputs

        # TODO: Make it more robust
        # Look for common final result names

        for final_key in ["final_result", "result", "answer", "output"]:
            if final_key in outputs:
                return outputs[final_key]
            
        # If no explicit final result, return the last output
        if outputs:
            last_output = list(outputs.values())[-1]
            return last_output
        
        return "Task completed successfully (no outputs generated)"
    
    def _add_to_history(self, role: MessageRole, content: str):
        """Adds a message to the conversation history."""
        self.conversation_history.append(MessageDict(role, content))

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        return len(self.tokenizer.encode(text))
    
    def get_plan_status(self) -> dict:
        """
        Returns current plan execution status.
        
        Returns:
            Dictionary with plan status information
        """

        if not self.current_plan:
            return {"status": "no_plan"}
        
        total_steps = len(self.current_plan.steps)
        current_step = self.current_plan.current_step_index
        executed_steps = sum(1 for step in self.current_plan.steps if step.executed)
        
        return {
            "status": "executing" if current_step < total_steps else "completed",
            "total_steps": total_steps,
            "current_step_index": current_step,
            "executed_steps": executed_steps,
            "outputs": dict(self.current_plan.outputs),
            "reasoning": self.current_plan.reasoning
        }
    
    def set_step_callback(self, callback):
        """
        Set or update the step callback function.
        
        Args:
            callback: Function that accepts (step_id, event_type, data) parameters
        """
        self.step_callback = callback

    def _notify_callback(self, step_id: str, event_type: str, data: dict = None):
        """
        Notify callback if it exists.
        
        Args:
            step_id: ID of the step
            event_type: Type of event ('started', 'completed', 'failed')
            data: Additional event data
        """
        if self.step_callback:
            try:
                self.step_callback(step_id, event_type, data or {})
            except Exception as e:
                logger.error(f"Error in step callback: {e}")

    def execute_plan_with_callback(self, plan_data: dict, callback, max_iterations: Optional[int] = None) -> str:
        """
        Execute a plan with step-by-step callbacks.
        
        Args:
            plan_data: The plan dictionary from planning phase
            callback: Function that accepts (step_id, event_type, data) parameters
            max_iterations: Override for maximum iterations
            
        Returns:
            Final execution result
        """
        # Set the callback
        self.step_callback = callback
        
        # Notify execution started
        if callback:
            try:
                callback('execution', 'started', {
                    'plan': plan_data,
                    'started_at': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error in execution callback: {e}")
        
        try:
            # Execute the plan
            result = self._execute_plan(plan_data, max_iterations)
            
            # Notify execution completed
            if callback:
                try:
                    callback('execution', 'completed', {
                        'result': result,
                        'completed_at': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error in execution callback: {e}")
            
            return result
            
        except Exception as e:
            # Notify execution failed
            if callback:
                try:
                    callback('execution', 'failed', {
                        'error': str(e),
                        'failed_at': datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error in execution callback: {e}")
            
            raise  # Re-raise the exception


