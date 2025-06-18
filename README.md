# AI Agent with Python

A custom-built AI agent system with tool-calling capabilities, designed for extensibility and direct system interaction without relying on third-party frameworks like LangChain or LangGraph.

## Overview

This project implements an autonomous AI agent that can:
- **Use Tools Dynamically**: Leverage a registry of tools to interact with files, execute commands, and more
- **Iterative Processing**: Make sequential decisions to accomplish complex tasks
- **State Management**: Maintain context and state across multiple interactions
- **Extensible Architecture**: Easy to add new tools and capabilities
- **LLM Agnostic**: Currently supports OpenAI with a pluggable interface for other providers

## Key Features

- **Framework-Free**: Built from scratch in Python without external agent frameworks
- **Tool System**: Extensible tool registry with JSON schema validation
- **Conversation Management**: Maintains conversation history with token management
- **Error Handling**: Robust error handling and validation at multiple layers
- **Logging**: Comprehensive logging system for debugging and monitoring
- **Type Safety**: Full type hints and structured response parsing

## Project Structure

```
llm-agent-python/
├── src/
│   ├── agent/              # Core agent logic
│   │   └── agent_core.py   # Main agent orchestration
│   ├── llm_interface/      # LLM provider abstractions
│   │   ├── base_llm_interface.py
│   │   └── openai_interface.py
│   ├── tooling/            # Tool system
│   │   ├── base_tool.py    # Abstract tool interface
│   │   ├── tool_registry.py # Tool management
│   │   └── tools/          # Individual tool implementations
│   │       ├── get_current_time_tool.py
│   │       └── list_files_tool.py
│   ├── prompts/            # System prompts and templates
│   │   └── agent_prompts.py
│   ├── config.py           # Configuration management
│   ├── logging.py          # Logging setup
│   └── main.py             # Application entry point
├── docs/                   # Documentation
├── logs/                   # Runtime logs
└── run.py                  # Command-line interface
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

### Basic Usage

```bash
python run.py "What time is it and list the files in the current directory?"
```

### Advanced Examples

```bash
# File exploration
python run.py "Show me all Python files in the src directory"

# Time-based queries  
python run.py "What's the current time and find all log files?"

# Multi-step tasks
python run.py "List all the Python files in the tooling directory and tell me what time it is"
```

## Architecture

### Core Components

1. **AgentCore**: Main orchestration layer that manages the conversation loop
2. **LLM Interface**: Abstraction layer for different LLM providers
3. **Tool Registry**: Manages available tools and their schemas
4. **Tools**: Individual capabilities (file operations, time queries, etc.)

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
