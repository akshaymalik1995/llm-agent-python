from typing import Optional
import json
from src.llm_interface.base_llm_interface import BaseLLMInterface
from src.tooling.tool_registry import ToolRegistry
from src.tooling.tool_selectors import KeywordToolSelector
from src.prompts.planning_prompt import PLANNING_PROMPT
from src.custom_logging import logger

# TODO: Have an interface for plan data
class PlanCreator:
    """Responsible for creating execution plans from user queries."""

    def __init__(self, llm_interface: BaseLLMInterface, tool_registry: ToolRegistry):
        self.llm_interface = llm_interface
        self.tool_registry = tool_registry

    def create_plan(self, user_query: str, max_tools: int = 4) -> Optional[dict]:
        """
        Creates an execution plan by calling the LLM with planning prompt

        Args:
            user_query:
                - The user's task request
            max_tools:
                - Maximum number of tools to include in plannning context

        Returns:
            Parsed plan data or None if planning failed
        """
        logger.info("Creating execution plan...")

        # Select relevant tools
        tool_selector = KeywordToolSelector(self.tool_registry)
        relevant_tools = tool_selector.select_relevant_tools(user_query, max_tools)

        logger.info(f"Selected tools: {relevant_tools}")

        # Format planning prompt
        tool_schemas_json = json.dumps(
            self.tool_registry.get_all_tools_info(relevant_tools), indent=2
        )

        planning_prompt = PLANNING_PROMPT.replace("{tools_schemas_json}", tool_schemas_json)

        logger.info(f"Planning prompt: {planning_prompt}")

        # Construct planning messages
        messages = [
            {"role": "system", "content": planning_prompt},
            {"role": "user", "content": f"Create an execution plan for: {user_query}"}
        ]

        try: 
            # Get plan from LLM
            response = self.llm_interface.get_completion(
                messages=messages,
                force_json=True
            )

            logger.info(f"Planning response received: {response}")

            # Parse the plan
            plan_data = json.loads(response.strip())

            logger.info(f"Plan created successfully with {len(plan_data['plan'])} steps")
            return plan_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse planning as JSON: {e}")
            print(f"Failed to parse planning as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            print("Planning failed: {e}")
            return None
