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
    def _format_system_prompt(self, template: str) -> str:
        """Formats the system prompt template with dynamic information like tool schemas."""
        tool_schemas_json = json.dumps(self.tool_registry.get_all_tools_info(), indent=2)
        return template.replace("{tool_schemas_json}", tool_schemas_json)

    def _add_to_history(self, role: MessageRole, content: str):
        """Adds a message to the conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def _construct_llm_prompt(self) -> list[dict]:
        """
        Constructs the full prompt for the LLM with intelligent token management.
        Preserves most important context while staying within token limits.
        """
        # Always include system prompt
        system_message = {"role": MessageRole.SYSTEM.value, "content": self._format_system_prompt(self.system_prompt_template)}
        messages = [system_message]
        
        # Count system prompt tokens
        current_tokens = self._count_message_tokens([system_message])
        
        if not self.conversation_history:
            return messages
        
        # Apply context management strategy
        managed_history = self._manage_context_window(self.conversation_history, self.effective_max_tokens - current_tokens)
        messages.extend(managed_history)
        
        final_token_count = self._count_message_tokens(messages)
        logger.info(f"Final prompt token count: {final_token_count}/{self.max_tokens}")
        
        return messages

    def _manage_context_window(self, history: list[MessageDict], available_tokens: int) -> list[MessageDict]:
        """
        Intelligent context window management with multiple strategies.
        
        Priority order:
        1. Always preserve initial user query
        2. Always preserve most recent conversation turn
        3. Summarize or truncate middle content
        4. Preserve tool results that are referenced later
        """
        if not history:
            return []
        
        # Strategy 1: Try to fit everything
        total_tokens = self._count_message_tokens(history)
        if total_tokens <= available_tokens:
            logger.info("All conversation history fits within token limit")
            return history
        
        logger.info(f"Context window management needed: {total_tokens} > {available_tokens}")
        
        # Strategy 2: Progressive truncation
        return self._progressive_truncation(history, available_tokens)

    def _progressive_truncation(self, history: list[MessageDict], available_tokens: int) -> list[MessageDict]:
        """
        Progressive truncation strategy that preserves the most important context.
        """
        if not history:
            return []
        
        # Always preserve first user message (the initial query)
        preserved_messages = [history[0]]
        remaining_history = history[1:]
        
        # Calculate tokens for preserved messages
        preserved_tokens = self._count_message_tokens(preserved_messages)
        available_for_rest = available_tokens - preserved_tokens
        
        if available_for_rest <= 0:
            logger.warning("Initial user query exceeds available tokens")
            return preserved_messages
        
        # Strategy: Keep recent context + important tool results
        managed_middle = self._manage_middle_context(remaining_history, available_for_rest)
        
        result = preserved_messages + managed_middle
        final_tokens = self._count_message_tokens(result)
        logger.info(f"After truncation: {final_tokens}/{available_tokens} tokens used")
        
        return result

    def _manage_middle_context(self, history: list[MessageDict], available_tokens: int) -> list[MessageDict]:
        """
        Manage the middle part of conversation history.
        Keeps recent context and important tool results.
        """
        if not history:
            return []
        
        # Strategy: Keep recent messages first, then work backwards
        recent_messages = []
        current_tokens = 0
        
        # Start from the most recent and work backwards
        for message in reversed(history):
            message_tokens = self._count_message_tokens([message])
            
            if current_tokens + message_tokens > available_tokens:
                # If this message would exceed limit, decide whether to include it
                if self._is_important_message(message):
                    # Try to summarize instead of dropping
                    summarized = self._summarize_message(message, available_tokens - current_tokens)
                    if summarized:
                        recent_messages.insert(0, summarized)
                        break
                else:
                    # Skip this message and continue
                    break
            
            recent_messages.insert(0, message)
            current_tokens += message_tokens
        
        # If we still have space and missed important context, add summary
        if current_tokens < available_tokens * 0.8:  # Use 80% threshold
            summary = self._create_context_summary(history, len(recent_messages))
            if summary:
                summary_tokens = self._count_message_tokens([summary])
                if current_tokens + summary_tokens <= available_tokens:
                    recent_messages.insert(0, summary)
        
        return recent_messages

    def _is_important_message(self, message: MessageDict) -> bool:
        """Determine if a message contains important context that shouldn't be lost."""
        content = message["content"].lower()
        
        # Important if it contains:
        # - Error messages
        # - Tool results with structured data
        # - User corrections or clarifications
        important_indicators = [
            "error:", "failed", "exception",
            "tool", "result:", "output:",
            "correction:", "actually", "instead",
            '"status": "success"', '"files":', '"total_items":'
        ]
        
        return any(indicator in content for indicator in important_indicators)

    def _summarize_message(self, message: MessageDict, max_tokens: int) -> MessageDict | None:
        """Summarize a message to fit within token constraints."""
        if max_tokens < 50:  # Minimum viable summary size
            return None
        
        content = message["content"]
        
        # If it's a tool result, extract key information
        if "tool" in content.lower() and "output:" in content.lower():
            return self._summarize_tool_result(message, max_tokens)
        
        # For other messages, truncate intelligently
        truncated_content = self._intelligent_truncate(content, max_tokens)
        if truncated_content:
            return {
                "role": message["role"],
                "content": f"[SUMMARIZED] {truncated_content}"
            }
        
        return None

    def _summarize_tool_result(self, message: MessageDict, max_tokens: int) -> MessageDict:
        """Summarize tool results to preserve key information."""
        content = message["content"]
        
        # Extract tool name and key results
        if "list_files" in content:
            # For file listing results, keep directory and count
            try:
                if '"total_items":' in content:
                    import re
                    path_match = re.search(r'"path": "([^"]+)"', content)
                    count_match = re.search(r'"total_items": (\d+)', content)
                    path = path_match.group(1) if path_match else "unknown"
                    count = count_match.group(1) if count_match else "unknown"
                    
                    summary = f"Tool list_files output: Listed {count} items in {path}"
                    return {"role": message["role"], "content": f"[SUMMARIZED] {summary}"}
            except:
                pass
        
        # Fallback: generic tool result summary
        summary = "Tool execution completed with results"
        return {"role": message["role"], "content": f"[SUMMARIZED] {summary}"}

    def _intelligent_truncate(self, content: str, max_tokens: int) -> str:
        """Intelligently truncate content while preserving meaning."""
        tokens = self.tokenizer.encode(content)
        if len(tokens) <= max_tokens:
            return content
        
        # Keep first and last portions
        keep_tokens = max_tokens - 10  # Reserve space for truncation indicator
        start_tokens = keep_tokens // 2
        end_tokens = keep_tokens - start_tokens
        
        start_text = self.tokenizer.decode(tokens[:start_tokens])
        end_text = self.tokenizer.decode(tokens[-end_tokens:])
        
        return f"{start_text}...[truncated]...{end_text}"

    def _create_context_summary(self, full_history: list[MessageDict], recent_count: int) -> MessageDict | None:
        """Create a summary of the conversation context that was truncated."""
        if recent_count >= len(full_history):
            return None
        
        truncated_history = full_history[:-recent_count] if recent_count > 0 else full_history
        
        # Count interactions and tool uses
        user_messages = len([m for m in truncated_history if m["role"] == "user"])
        tool_uses = len([m for m in truncated_history if "tool" in m["content"].lower()])
        
        summary_content = f"[CONTEXT SUMMARY] Previous conversation: {user_messages} user messages, {tool_uses} tool executions. Focus on recent context below."
        
        return {
            "role": MessageRole.SYSTEM.value,
            "content": summary_content
        }

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
            logger.info("Parsed LLM response: %s", parsed_response)

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



