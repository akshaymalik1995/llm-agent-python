from src.tooling.tool_registry import ToolRegistry
import json
from src.llm_interface.base_llm_interface import BaseLLMInterface
from src.config import settings
from typing import TypedDict, Union
import enum
from src.logging import logger
import tiktoken

class LLMResponseType(enum.Enum):
    TOOL_CALL = "tool_call"
    ANSWER = "answer"

class ToolCallResponse(TypedDict):
    type: LLMResponseType.TOOL_CALL
    thought: str
    tool_name: str
    arguments: dict

class AnswerResponse(TypedDict):
    type: LLMResponseType.ANSWER
    content: str

class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

LLMResponse = Union[ToolCallResponse, AnswerResponse]

class MessageDict(TypedDict):
    role: MessageRole
    content: str


class AgentCore:
    def __init__(self, llm_interface: BaseLLMInterface, tool_registry: ToolRegistry, system_prompt_template: str | None = None):
        """
        Initializes the AI Agent

        Args:
            llm_interface: An object responsible for interacting with the LLM.
                           This could be a wrapper around an API client or a local model.
            tool_registry: An instance of ToolRegistry containing available tools.
            system_prompt: A base system prompt to guide the LLM's behavior.
        """

        self.llm_interface = llm_interface
        self.tool_registry = tool_registry
        self.conversation_history: list[MessageDict] = []  # Stores conversation history as a list of dicts
        self.max_iterations = settings.MAX_AGENT_ITERATIONS # Default maximum iterations to prevent infinite loops

        self.system_prompt_template = system_prompt_template or settings.DEFAULT_SYSTEM_PROMPT_TEMPLATE

        self.max_tokens = 25000  # Your target limit
        self.token_buffer = 2000  # Safety buffer for response generation
        self.effective_max_tokens = self.max_tokens - self.token_buffer
        
        # Initialize tokenizer (using GPT-4 tokenizer as standard)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")

        # Initialize state for the agent to update across iterations
        self.state = {}

    def _format_system_prompt(self, template: str) -> str:
        """Formats the system prompt template with dynamic information like tool schemas."""
        tool_schemas_json = json.dumps(self.tool_registry.get_all_tools_info(), indent=2)
        return template.replace("{tool_schemas_json}", tool_schemas_json)

    def _add_to_history(self, role: MessageRole, content: str):
        """Adds a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def _construct_llm_prompt(self) -> list[dict]:
        """
        Constructs the full prompt for the LLM, including system prompt
        and conversation history.
        The format (list of dicts) depends on the LLM API (e.g., OpenAI's chat format).
        """
        messages = [{"role": MessageRole.SYSTEM.value, "content": self._format_system_prompt(self.system_prompt_template)}]

        
        messages.extend(self.conversation_history) # TODO: Explore options to truncate or summarize the history
        return messages

    def _parse_llm_response(self, response_text: str) -> dict:
        """
        Parses the LLM's JSON response into a typed structure.
        Returns None if parsing fails or if the response is not in expected format.
        """
        if not response_text or not response_text.strip():
            # If the response is empty or just whitespace, return a default answer
            print("Error: LLM response is empty or whitespace.")
            return None
        try:
            parsed = json.loads(response_text.strip())
            
            # Validate response structure
            if "type" not in parsed:
                print(f"Error: LLM response does not contain 'type' field: {parsed}")
                return None
            
            # First, parse the state if it exists
            if "state" in parsed:
                if not isinstance(parsed["state"], dict):
                    print(f"Error: LLM response 'state' field is not a valid JSON object: {parsed['state']}")
                    return None
                self.state.update(parsed["state"])
                # Add state to conversation history
                logger.info(f"State updated: {json.dumps(self.state, indent=2)}")
                self._add_to_history(MessageRole.SYSTEM.value, f"State updated: {json.dumps(self.state, indent=2)}")
            
            response_type = parsed["type"]

            if response_type == LLMResponseType.TOOL_CALL.value:
                # Validate tool call response structure
                required_fields = {"type", "thought", "tool_name", "arguments"}
                if not required_fields.issubset(parsed.keys()):
                    print(f"Error: LLM tool call response is missing required fields: {parsed}")
                    return None
                return ToolCallResponse(parsed)
            
            elif response_type == LLMResponseType.ANSWER.value:
                # Validate answer response structure
                if "content" not in parsed:
                    print(f"Error: LLM answer response is missing 'content' field: {parsed}")
                    return None
                return AnswerResponse(parsed)
            else:
                print(f"Error: LLM response has unknown type '{response_type}': {parsed}")
                return None

        except json.JSONDecodeError:
            print(f"Error: Failed to parse LLM response as JSON: {response_text}")
            print(f"Raw response: {response_text}")
            return None
        except Exception as e:
            print(f"Error: Unexpected error while parsing LLM response: {e}")
            return None
        
    
    def execute_task(self, user_query: str, max_iterations: int = None) -> str:
        """
        Manages the iterative execution of a task.

        Args:
            user_query: The initial query or task from the user.
            max_iterations: Override for the maximum number of agent iterations.

        Returns:
            The final result or response from the agent.
        """

        current_iterations = 0

        if max_iterations is None:
            max_iterations = self.max_iterations

        self._add_to_history(MessageRole.USER.value, user_query)

        while current_iterations < max_iterations:
            current_iterations += 1
            logger.info(f"Iteration {current_iterations}/{max_iterations}")

            llm_prompt_messages = self._construct_llm_prompt()

            prompt_tokens = self._count_message_tokens(llm_prompt_messages)
            logger.info(f"Sending prompt with {prompt_tokens} tokens to LLM")

            # --- 1. LLM Call ---

            llm_response_text = self.llm_interface.get_completion(messages=llm_prompt_messages)
            logger.info("LLM response received: %s", llm_response_text)

            


            if not llm_response_text:
                return "Error: LLM did not provide a response."
            
             

            # --- 2. Parse LLM Response ---
            parsed_response = self._parse_llm_response(llm_response_text)

            if not parsed_response:
                return "Error: Failed to parse LLM response. Please check the response format."
            
            # Add raw response
            self._add_to_history(MessageRole.ASSISTANT.value, llm_response_text)

            if parsed_response["type"] == LLMResponseType.TOOL_CALL.value:
                success = self._handle_tool_call(parsed_response)
                if not success:
                    # Continue to next iteration to let LLM try again
                    continue
            
            
            elif parsed_response["type"] == LLMResponseType.ANSWER.value:
                answer = parsed_response["content"]
                self._add_to_history(role=MessageRole.ASSISTANT.value, content=answer)
                return answer # Task considered complete
            
            else:
                # Should not happen with current parsing
                self._add_to_history(role=MessageRole.SYSTEM.value, content="Error: Unknown parsed action type.")
                return "Error: Internal agent error in parsing LLM response."
        
        return "Agent reached maximum iterations without completing the task."
    
    def _handle_tool_call(self, tool_call: ToolCallResponse) -> bool:
        """Handle a tool call response. Returns True if successful, False otherwise."""
        tool_name = tool_call['tool_name']
        arguments = tool_call["arguments"]
        thought = tool_call["thought"]

        self._add_to_history(MessageRole.ASSISTANT.value, f"Thought: {thought} \nUsing tool: {tool_name}")

        print(f"Agent Thought: {thought}")
        print(f"Agent using tool: {tool_name} with arguments: {arguments}")

        tool = self.tool_registry.get_tool(tool_name)

        if not tool:
            error_message = f"Error: Unknown tool '{tool_name}'"
            self._add_to_history(MessageRole.SYSTEM.value, error_message)
            print(error_message)
            return False
        
        try:
            tool_result = tool.execute(arguments)
            logger.info(f"Tool {tool_name} executed successfully with result: {tool_result}")
            self._add_to_history(MessageRole.ASSISTANT.value, f"Tool {tool_name} output: {tool_result}")
            print(f"Tool result: {tool_result}")
            return True
        except Exception as e:
            error_message = f"Error executing tool {tool_name}: {str(e)}"
            self._add_to_history(MessageRole.SYSTEM, error_message)
            print(error_message)

    def _count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        return len(self.tokenizer.encode(text))
    
    def _count_message_tokens(self, messages: list[dict]) -> int:
        """Count total tokens in a list of messages."""
        total_tokens = 0
        for message in messages:
            # Account for message structure overhead (role, formatting, etc.)
            total_tokens += 4  # Overhead per message
            total_tokens += self._count_tokens(message["content"])
        return total_tokens



