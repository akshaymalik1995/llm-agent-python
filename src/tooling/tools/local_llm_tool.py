import json
from typing import List, Optional
from src.tooling.base_tool import BaseTool
from src.llm_interface.openai_interface import OpenAIInterface

class LocalLLMTool(BaseTool):
    """"
    A tool for interacting with local LLMs via HTTP API.
    """

    def __init__(self, model_name: str = "llama3.1", 
                 base_url: str = "http://localhost:11434/v1"):
        self.model_name = model_name
        self.base_url = base_url
        self._local_llm_interface = None

    @property
    def local_llm_interface(self) -> OpenAIInterface:
        """Lazy initialization of local LLM interface."""
        if self._local_llm_interface is None:
            self._local_llm_interface = OpenAIInterface(
                model_name=self.model_name,
                api_key="dummy",  # Local LLMs typically don't need API keys
                base_url=self.base_url
            )
        return self._local_llm_interface
    
    @property
    def name(self) -> str:
        return "use_local_llm"
    
    @property
    def keywords(self) -> List[str]:
        return [
            "consult", "ask", "local", "llm", "model", "opinion", "perspective",
            "analyze", "review", "second", "alternative", "private", "offline",
            "validate", "check", "confirm", "specialized", "domain", "local_ai"
        ]
    
    @property
    def signature(self) -> str:
        return "use_local_llm(query: str, context: str = '', task_type: str = 'general') -> response"
    
    @property
    def description(self) -> str:
        return """
        Use a local LLM whenever asked to.
        """
    
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question, task, or request for the local LLM"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context, background information, or data to provide"
                },
                "system_prompt": {
                    "type": "string",
                    "description": "Optional custom system prompt to guide the model's behavior"
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "description": "Controls randomness (0.0 = deterministic, 2.0 = very creative)"
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4096,
                    "description": "Maximum number of tokens to generate"
                }
            },
            "required": ["query"]
        }
    
    @property
    def response_format(self) -> dict:
        return {
            "status": "string",
            "response": "string", 
            "model_used": "string",
            "processing": "string",
            "message": "string"
        }
    
    def execute(self, args: dict) -> str:
        try:
            query = args.get("query", "").strip()
            context = args.get("context", "").strip()
            custom_system_prompt = args.get("system_prompt", "").strip()
            temperature = args.get("temperature", 0.7)
            max_tokens = args.get("max_tokens", 1000)

            if not query:
                return json.dumps({
                    "status": "error",
                    "message": "Query is required for local LLM consultation"
                })
            
            system_prompt = custom_system_prompt or self._get_default_system_prompt()

            # Construct the full prompt
            full_prompt = self._construct_prompt(query, context)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ]

            # Call local LLM with specified parameters
            response = self.local_llm_interface.get_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            if response:
                return json.dumps({
                    "status": "success",
                    "response": response,
                    "model_used": self.model_name,
                    "processing": "local"
                }, indent=2)
            
            else:
                return json.dumps({
                    "status": "error",
                    "message": "No response received from local LLM",
                    "model_attempted": self.model_name,
                })
            
        except Exception as e:
            return json.dumps({
                    "status": "error", 
                    "message": f"Error during local LLM usage: {str(e)}",
                    "model": self.model_name,
                })
        
    def _get_default_system_prompt(self):
        return """You are a helpful assistant."""
    
    def _construct_prompt(self, query: str, context: str) -> str:
        """Consult the full prompt for the Local LLM Usage"""
        prompt_parts = []

        if context:
            prompt_parts.append(f"Context: {context}")

        prompt_parts.append(f"Query: {query}")

        return "\n\n".join(prompt_parts)