import os
from dotenv import load_dotenv
from pathlib import Path
from src.prompts.agent_prompts import EXECUTION_SYSTEM_PROMPT

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"

if DOTENV_PATH.exists():
    load_dotenv(DOTENV_PATH)
else:
    # TODO:
    # You might want to print a warning or log if .env is expected but not found
    # print(f"Warning: .env file not found at {DOTENV_PATH}")
    pass


class AppConfig:
    """
    Application configuration settings.
    """

    # LLM API Keys - Loaded from environment variables for security
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    # Default LLM settings
    DEFAULT_OPENAI_MODEL: str = "gpt-4o" # Or "gpt-3.5-turbo"
    DEFAULT_GEMINI_MODEL: str = "gemini-1.5-pro-latest" # Or other appropriate model

    OLLAMA_MODEL = "tinyllama"
    OLLAMA_ENDPOINT = "http://localhost:11434/v1"  # Default Ollama endpoint

    # Agent settings
    MAX_AGENT_ITERATIONS: int = 20

    # For local models (example)
    LOCAL_MODEL_BASE_URL: str | None = os.getenv("LOCAL_MODEL_BASE_URL") # e.g., "http://localhost:11434/v1" for Ollama OpenAI-compatible API
    DEFAULT_LOCAL_MODEL_NAME: str | None = os.getenv("DEFAULT_LOCAL_MODEL_NAME")

    DEFAULT_SYSTEM_PROMPT_TEMPLATE: str = EXECUTION_SYSTEM_PROMPT

    # Context settings
    MAX_CONTEXT_TOKENS: int = 25000
    CONTEXT_TOKEN_BUFFER: int = 2000  # Reserve for response generation
    CONTEXT_SUMMARY_THRESHOLD: float = 0.8  # When to add context summary

# Create a single instance of the config to be imported by other modules
settings = AppConfig()

