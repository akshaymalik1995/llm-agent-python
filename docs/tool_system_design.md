# AI Agent - Tool System Design

This document outlines the design and implementation flow for the tool system used by the AI agent.

## 1. Core Objectives

    - Enable the LLM to utilize a variety of functions (tools) to interact with the environment (e.g., file system, command line).
    - Ensure the tool system is extensible, allowing new tools to be added easily.
    - Provide clear definitions and schemas for tools so the LLM can understand how to use them.
    - Implement robust error handling and validation.
  
## 2. Tool Interface (Base `BaseTool` Class)

Defines the contract that all tools must adhere to.

### 2.1. Properties

-   `name` (str):
    -   Purpose: Unique machine-readable identifier.
    -   Example: `"edit_file"`, `"execute_command"`
-   `description` (str):
    -   Purpose: Human-readable (and LLM-readable) explanation of the tool's function, capabilities, and expected arguments.
    -   Example: `"Modifies a file by creating, overwriting, or appending content. Arguments: 'file_path' (string), 'content' (string), 'operation' (string: 'create', 'overwrite', 'append')."`
-   `input_schema` (dict):
    -   Purpose: JSON schema defining the structure and types of expected input arguments. Used for validation and LLM guidance.
    -   Example:
        ```json
        {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "The target file path."},
                "content": {"type": "string", "description": "Content to write or append."},
                "operation": {"type": "string", "enum": ["create", "overwrite", "append"], "description": "The file operation to perform."}
            },
            "required": ["file_path", "content", "operation"]
        }
        ```

### 2.2. Methods

-   `execute(self, args: dict) -> str`:
    -   Purpose: Core method that performs the tool's action.
    -   Input: A dictionary of arguments validated against `input_schema`.
    -   Output: A string (potentially JSON formatted) representing the result (success, data, or error).
-   `get_tool_info(self) -> dict`:
    -   Purpose: Helper to return a structured dictionary of `name`, `description`, and `input_schema`.

## 3. Tool Registry (`ToolRegistry` Class)

Manages the collection of available tools.

### 3.1. Responsibilities

-   Register new tools.
-   Retrieve a specific tool by its name.
-   Provide a list of all available tools (their info/schemas) to the agent/LLM.

### 3.2. Proposed Implementation

-   Internal storage: Dictionary mapping `tool_name` to `BaseTool` instance.
-   Methods:
    -   `register_tool(self, tool: BaseTool)`
    -   `get_tool(self, tool_name: str) -> BaseTool | None`
    -   `get_all_tools_info(self) -> list[dict]`

## 4. Agent-Tool Interaction Flow (Execution Cycle)

Describes how the agent uses the LLM and tools to perform tasks.

1.  **Prompt Construction:**
    -   Agent provides the LLM with the current task, conversation history, and a list of available tools (from `ToolRegistry.get_all_tools_info()`).
    -   The prompt will instruct the LLM on how to format its response if it wishes to use a tool (e.g., a specific JSON structure specifying `tool_name` and `arguments`).
2.  **LLM Processing:**
    -   LLM analyzes the prompt and decides if a tool is needed.
    -   If so, LLM generates a response indicating the chosen tool and its arguments.
3.  **Response Parsing:**
    -   Agent parses the LLM's response.
    -   If a tool call is indicated:
        -   Extract `tool_name` and `arguments`.
4.  **Argument Validation (Optional but Recommended):**
    -   Retrieve the `input_schema` for the chosen tool.
    -   Validate the LLM-provided `arguments` against this schema.
    -   Handle validation errors by informing the LLM or requesting correction.
5.  **Tool Execution:**
    -   Retrieve the `BaseTool` instance from `ToolRegistry` using `tool_name`.
    -   Call the tool's `execute(arguments)` method.
6.  **Result Processing:**
    -   The string output from `execute()` is captured.
    -   This result is added to the conversation history and provided back to the LLM in the next turn, allowing it to see the outcome of its action.
7.  **Iteration:**
    -   The cycle repeats until the task is completed or a stopping condition is met.


## 5. Initial Tool Implementations

- The design will be documented with the specific tool implementation whenever it is created.

## 6. Error Handling and Validation

-   **Tool Input Validation:** Use the `input_schema` to validate arguments passed to `execute()`.
-   **Tool Execution Errors:** Tools should catch their own exceptions and return structured error messages.
-   **Agent-Level Errors:** The agent should handle:
    -   LLM requesting a non-existent tool.
    -   LLM providing malformed arguments.
    -   Tool execution failures not caught by the tool itself.
    -   These errors should be fed back to the LLM for correction or alternative actions.


## 7. Security Considerations
-   **`ExecuteCommandTool`:** This is the most sensitive.
    -   Clearly document risks.
    -   Consider running in a sandboxed environment if possible.
    -   Initially, the LLM provides the full command. If the design evolves to construct commands from LLM-provided parts, extreme care is needed to prevent injection.


## 8. Future Extensibility

-   Adding new tools should involve:
    1.  Creating a new class inheriting from `Tool`.
    2.  Implementing the required properties and methods.
    3.  Registering an instance of the new tool with the `ToolRegistry`.
-   The system should not require modification to the core agent loop to accommodate new tools.






