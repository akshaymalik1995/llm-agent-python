from src.tooling.base_tool import BaseTool
from typing import List

class ToolRegistry:
    def __init__(self):
        self._tools = {}  # Stores tool_name: tool_instance

    def register_tool(self, tool: BaseTool):
        if tool.name in self._tools:
            print(f"Warning: Tool '{tool.name}' is already registered. Overwriting.")
        self._tools[tool.name] = tool
        print(f"Tool '{tool.name}' registered.")

    def get_tool(self, tool_name: str) -> BaseTool | None:
        return self._tools.get(tool_name)
    
    def get_all_tools_info(self, tools: List[str] = None) -> list[dict]:
        """
        Returns a list of schemas for all registered tools.
        This is what you'd pass to the LLM in its system prompt.
        """
        if tools:
            return [self._tools[tool_name].get_tool_info() for tool_name in tools if tool_name in self._tools]
        return [tool.get_tool_info() for tool in self._tools.values()]