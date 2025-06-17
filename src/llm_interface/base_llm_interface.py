from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseLLMInterface(ABC):
    """
    Abstract base class for Large Language Model interfaces.
    Defines the contract for interacting with different LLMs.
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None, **kwargs: Any):
        """
        Initializes the LLM interface.

        Args:
            model_name (str): The specific model to use (e.g., "gpt-3.5-turbo", "gemini-pro").
            api_key (Optional[str]): The API key for the LLM service, if required.
            **kwargs: Additional keyword arguments for specific LLM configurations.
        """

        self.model_name = model_name
        self.api_key = api_key
        self.config = kwargs # Store other configurations

        @abstractmethod
        def get_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> Optional[str]:
            """
            messages (List[Dict[str, str]]): A list of message dictionaries,
                typically following a format like:
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Who won the world series in 2020?"}
                ]

            **kwargs: Additional keyword arguments that might be specific to an LLM's
                      completion endpoint (e.g., temperature, max_tokens).

            Returns:
            Optional[str]: The LLM's response content as a string, or None if an error occurs.
            """
            pass

        def _prepare_request_data(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
            """
            (Optional) Helper method to prepare the data payload for the LLM API request.

            This can be overridden by subclasses if they have very different request structures.
            """

            request_data = {
                "model": self.model_name,
                "messages": messages,
                **self.config, # Include base configurations
                **kwargs      # Override with call-specific configurations
            }
            return request_data
        
        def __repr__(self) -> str:
            return f"<{self.__class__.__name__}(model='{self.model_name}')>"