# AI Agent with Planning-Based Execution

A sophisticated AI agent system built from scratch with **planning-first architecture**, designed for complex multi-step task execution without relying on third-party frameworks like LangChain or LangGraph.

## Overview

This project implements an autonomous AI agent that uses a **two-phase execution model**:

### 🧠 **Planning Phase**
- Analyzes user requests and creates detailed execution plans
- Breaks down complex tasks into structured, sequential steps
- Supports conditional logic, loops, and iterative refinement
- Estimates resource requirements and iteration limits

### ⚡ **Execution Phase**
- Follows pre-created plans step-by-step
- Executes LLM calls and tool operations deterministically
- Manages variable references and data flow between steps
- Handles control flow (conditions, jumps, loops)

**Key Capabilities:**
- **Complex Task Orchestration**: Multi-step workflows with branching logic
- **Iterative Processing**: Built-in support for critique-and-improve cycles
- **Tool Integration**: Extensible tool registry with JSON schema validation  
- **Variable Management**: Data flows seamlessly between execution steps
- **Framework-Free**: Pure Python implementation with complete control

## Key Features

- **🎯 Planning-First Architecture**: Creates complete execution plans before starting work
- **🔄 Complex Workflows**: Supports iterative processes, conditional branching, and loops
- **⚙️ Tool Integration**: Extensible tool system for environment interaction
- **📊 Variable Management**: Seamless data flow between execution steps
- **🚫 Framework-Free**: Built from scratch without external agent dependencies
- **🔍 Full Observability**: Comprehensive logging of plans, execution, and state changes
- **⏱️ Resource Management**: Built-in iteration limits and token management
- **🎨 Flexible LLM Interface**: Pluggable support for different LLM providers

## Real-World Example

```bash
python run.py "Write an essay on Liberalism? Critique and Improve it 3 times."
```

**What happens:**
1. **Planning Phase**: Creates 9-step execution plan
2. **Execution Phase**: 
   - Step L1: Write initial essay
   - Step L2: Generate detailed critique  
   - Step L3: Improve essay based on critique
   - Step L4: Second critique round
   - Step L5: Second improvement round
   - Step L6: Third critique round
   - Step L7: Final improvement
   - Step L8: Present final result with summary
   - Step END: Complete execution

The agent automatically manages variable references (`{essay}`, `{critique1}`, etc.) and produces a polished final essay through systematic iteration.

## Project Structure

```
llm-agent-python/
├── src/
│   ├── agent/                    # Core agent logic
│   │   ├── agent_core.py         # Planning & execution orchestration
│   │   └── types.py              # Plan and execution data structures
│   ├── llm_interface/            # LLM provider abstractions
│   │   ├── base_llm_interface.py # Abstract LLM interface
│   │   └── openai_interface.py   # OpenAI implementation
│   ├── tooling/                  # Tool system
│   │   ├── base_tool.py          # Abstract tool interface
│   │   ├── tool_registry.py      # Tool management and discovery
│   │   └── tools/                # Individual tool implementations
│   │       ├── get_current_time_tool.py
│   │       └── list_files_tool.py
│   ├── prompts/                  # System prompts and templates
│   │   ├── agent_prompts.py      # Execution-time prompts
│   │   └── planning_prompt.py    # Planning-phase prompts
│   ├── config.py                 # Configuration management
│   ├── logging.py                # Logging setup
│   └── main.py                   # Application entry point
├── docs/                         # Documentation
├── logs/                         # Runtime execution logs
└── run.py                        # Command-line interface
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- OpenAI API key (for LLM interface)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/akshaymalik1995/llm-agent-python
cd llm-agent-python
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install openai python-dotenv tiktoken
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

## Usage

### Simple Tasks

```bash
# Basic information queries
python run.py "What time is it?"

# File system exploration  
python run.py "List all Python files in the src directory"
```

### Complex Multi-Step Tasks

```bash
# Iterative content creation
python run.py "Write an essay on climate change, then critique and improve it twice"

# Research and analysis workflows
python run.py "List all tools available, analyze their purposes, and suggest improvements"

# Conditional processing
python run.py "Create a summary of the project structure, and if it's complex, provide implementation recommendations"
```

### Task Complexity Examples

**Simple Task:** Direct answers or single tool calls
```
Query: "What time is it?"
Plan: 1 step (tool call)
```

**Medium Task:** Sequential steps with data flow
```  
Query: "List Python files and analyze their structure"
Plan: 2-3 steps (tool → analysis → summary)
```

**Complex Task:** Iterative refinement with conditions
```
Query: "Write and improve content until it's excellent" 
Plan: 6+ steps with loops and conditional logic
```

## Architecture Deep Dive

### Two-Phase Execution Model

#### Phase 1: Planning 🧠
```
User Query → Planning LLM Call → Structured Execution Plan
```

The planning phase creates a detailed JSON execution plan:

```json
{
  "plan": [
    {
      "id": "L1",
      "type": "llm", 
      "description": "Write initial essay",
      "prompt": "Write a comprehensive essay on...",
      "output_name": "essay"
    },
    {
      "id": "L2",
      "type": "llm",
      "description": "Critique the essay", 
      "prompt": "Provide detailed critique of: {essay}",
      "input_refs": ["essay"],
      "output_name": "critique"
    },
    {
      "id": "C1",
      "type": "if",
      "condition": "critique_score >= 8", 
      "goto_id": "END"
    },
    {
      "id": "END",
      "type": "end"
    }
  ],
  "max_iterations": 10,
  "reasoning": "Iterative improvement workflow..."
}
```

#### Phase 2: Execution ⚡
```
Plan → Step-by-Step Execution → Variable Management → Final Result
```

The execution engine:
1. **Processes each step sequentially**
2. **Resolves variable references** (`{essay}` → actual content)
3. **Handles control flow** (conditions, jumps, loops)
4. **Manages state** across all steps

### Step Types

| Type | Purpose | Example Use Case |
|------|---------|------------------|
| `llm` | Language model calls | Content generation, analysis, reasoning |
| `tool` | Environment interaction | File operations, API calls, system commands |
| `if` | Conditional branching | Quality checks, decision points |
| `goto` | Flow control | Loops, retry logic |
| `end` | Termination | Mark completion |

### Variable System

Variables flow between steps using references:

```json
{
  "prompt": "Improve this text: {original_text} based on: {feedback}",
  "input_refs": ["original_text", "feedback"]
}
```

The execution engine automatically:
- **Resolves references** to actual values
- **Maintains variable scope** across steps  
- **Validates dependencies** before execution

### Tool System

Tools are the primary way the agent interacts with the environment. Each tool:
- Inherits from `BaseTool`
- Defines a JSON schema for input validation
- Returns structured JSON responses

#### Creating Custom Tools

```python
from src.tooling.base_tool import BaseTool
import json

class MyCustomTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_custom_tool"
    
    @property
    def description(self) -> str:
        return "Description of what this tool does"
    
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param1"]
        }
    
    def execute(self, args: dict) -> str:
        # Tool implementation
        return json.dumps({"status": "success", "result": "..."})
```

### Available Tools

#### `get_current_time`
- **Purpose**: Returns current date and time
- **Arguments**: None
- **Example**: `{"type": "tool_call", "tool_name": "get_current_time", "arguments": {}}`

#### `list_files`
- **Purpose**: Lists files in directories with powerful filtering
- **Features**: Pattern matching, file details, sorting, hidden files
- **Arguments**: `path`, `pattern`, `name_contains`, `extensions`, `show_hidden`, `show_details`, `sort_by`
- **Limit**: Maximum 20 files returned for LLM context management

## Configuration

Key configuration options in config.py:

```python
class AppConfig:
    # LLM Settings
    DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
    
    # Agent Settings  
    MAX_AGENT_ITERATIONS = 10
    MAX_CONTEXT_TOKENS = 25000
    CONTEXT_TOKEN_BUFFER = 2000
```

## Response Format

The agent uses structured JSON responses:

```json
{
  "type": "tool_call",
  "thought": "Reasoning for using this tool",
  "tool_name": "exact_tool_name", 
  "arguments": {"param": "value"},
  "state": {"key": "value"}
}
```

Or for final answers:

```json
{
  "type": "answer",
  "content": "Final response to user",
  "thought": "Reasoning for this answer",
  "state": {"key": "value"}
}
```

## Logging

All agent interactions are logged to timestamped files in the logs directory:
- Conversation history
- Tool executions
- State changes
- Error conditions

## Security Considerations

- **API Keys**: Stored in environment variables, not in code
- **Tool Validation**: All tool inputs validated against JSON schemas
- **Error Isolation**: Tool failures don't crash the agent
- **Token Limits**: Built-in protection against excessive token usage

## Extending the System

### Adding New LLM Providers

1. Inherit from `BaseLLMInterface`
2. Implement `get_completion()` method
3. Update configuration for new provider

### Adding New Tools

1. Create tool class inheriting from `BaseTool`
2. Implement required properties and `execute()` method
3. Register tool in main.py

### Customizing Prompts

Modify agent_prompts.py to adjust system behavior and response formatting.

## Known Limitations

- **Tool Limit**: `list_files` returns maximum 20 files per call
- **Token Management**: Basic token counting, no advanced context compression
- **Error Recovery**: Limited automatic error recovery strategies
- **Concurrency**: No parallel tool execution

## Development

### Debug Mode
Check logs in `logs/agent_YYYYMMDD_HHMMSS.log` for detailed execution traces.

## Contributing

1. Follow existing code structure and type hints
2. Add comprehensive docstrings
3. Update tool registry when adding new tools
4. Test with various query types

---

**Note**: This is a learning/research project demonstrating agent architecture patterns.
