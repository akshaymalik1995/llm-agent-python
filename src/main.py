
from src.config import settings
from src.llm_interface.openai_interface import OpenAIInterface
from src.tooling.tool_registry import ToolRegistry
from src.tooling.tools import GetCurrentTimeTool
from src.agent.agent_core import AgentCore

def run_agent(query: str):
    """
    Initializes and runs the AI agent.
    """

    if not query.strip(): # Check if the provided query is empty
        print("No query provided. Exiting.")
        return

    print("Initializing AI Agent...")

    # 1. Initialize LLM Interface
    # Choose your LLM interface. For now, we'll use OpenAI as an example.
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not found in environment variables or .env file.")
        print("Please set it to run the agent with OpenAI.")
        return
    
    # You can choose the model from config or override here
    llm_interface = OpenAIInterface(
        model_name=settings.DEFAULT_OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY
        # You can add other kwargs from settings if needed, e.g., temperature
        # temperature=settings.DEFAULT_TEMPERATURE 
    )

    print(f"Using LLM: OpenAI")

    # 2. Initialize Tool Registry and Register Tools
    tool_registry = ToolRegistry()

    time_tool = GetCurrentTimeTool()
    tool_registry.register_tool(time_tool)

    print(f"Registered tools: {[tool_info['name'] for tool_info in tool_registry.get_all_tools_info()]}")

    # 3. Initialize AgentCore
    # You can use the default system prompt from config or customize it
    agent = AgentCore(
        llm_interface=llm_interface,
        tool_registry=tool_registry,
    )

    print("Agent initialized")

    # 4. Interaction Loop

    print("Agent is thinking...")

    try:
        agent_response = agent.execute_task(query)
        # The agent_response is already printed by AgentCore for now,
        # but you might want to handle its display here for more control.
        # print(f"\nAgent Response:\n{agent_response}")
    except Exception as e:
        print(f"An error occurred during task execution: {e}")
        # Optionally, re-initialize agent or clear history for a fresh start
        # TODO:
        # agent.conversation_history.clear() 