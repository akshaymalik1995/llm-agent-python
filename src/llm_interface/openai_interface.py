from typing import List, Dict, Any, Optional
from src.llm_interface.base_llm_interface import BaseLLMInterface
from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError
from src.config import settings


class OpenAIInterface(BaseLLMInterface):
    """
    LLM Interface implementation for OpenAI models.
    """
    def __init__(self, model_name: str = settings.DEFAULT_OPENAI_MODEL, api_key: Optional[str] = None, **kwargs: Any):
        """"
        Initializes the OpenAI LLM interface.

        Args:
            model_name (str): The OpenAI model to use (e.g., "gpt-4", "gpt-3.5-turbo").
            api_key (Optional[str]): The OpenAI API key. If None, it will try to use
                                     the OPENAI_API_KEY environment variable.
            **kwargs: Additional keyword arguments for OpenAI client or completion.
        """

        resolved_api_key = api_key or settings.OPENAI_API_KEY

        if not resolved_api_key:
            # Consider raising an error or logging a warning more explicitly
            print("Warning: OpenAI API key not provided or found in environment variables.")

        super().__init__(model_name=model_name, api_key=resolved_api_key, **kwargs)

        try:
            self.client = OpenAI(api_key=self.api_key)
            # You can also pass other OpenAI client options from self.config if needed
            # e.g., self.client = OpenAI(api_key=self.api_key, base_url=self.config.get("base_url"))
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            self.client = None # type: ignore

    def get_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> Optional[str]:
        """
        Gets a completion from the OpenAI API.

        Args:
            messages (List[Dict[str, str]]): A list of message dictionaries.
            **kwargs: Additional keyword arguments for the OpenAI completion call
                      (e.g., temperature, max_tokens, top_p).

        Returns:
            Optional[str]: The LLM's response content as a string, or None if an error occurs.
        """

        if not self.client:
            print("Error: OpenAI client not initialized.")
            return None
        
        if not self.api_key: # Double check, though client init might fail first
            # Though OPENAI Client automatically picks up the API key from environment variables
            print("Error: OpenAI API key is missing.")
            # return None

        request_data = self._prepare_request_data(messages, **kwargs)

        # Force JSON response format
        request_data["response_format"] = {"type": "json_object"}

        # Ensure only valid OpenAI parameters are passed
        valid_openai_params = {"temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop","response_format"}

        completion_kwargs = {k: v for k, v in request_data.items() if k in valid_openai_params and k not in ["model", "messages"]}

        # Add model and messages separately as they are primary arguments for chat.completions.create
        completion_kwargs["model"] = request_data["model"]
        completion_kwargs["messages"] = request_data["messages"]

        try:
            # print(f"DEBUG: Sending to OpenAI: {completion_kwargs}") # For debugging
            response = self.client.chat.completions.create(**completion_kwargs) # type: ignore

            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                return content.strip() if content else None
            else:
                print(f"Warning: OpenAI response did not contain expected choices or message: {response}")
                return None
            
        except APIConnectionError as e:
            print(f"OpenAI API Connection Error: {e}")
        except RateLimitError as e:
            print(f"OpenAI API Rate Limit Error: {e}")
        except APIStatusError as e:
            print(f"OpenAI API Status Error (HTTP Status {e.status_code}): {e.response}")
        except Exception as e:
            print(f"An unexpected error occurred while calling OpenAI API: {e}")

        return None
    
    def _prepare_request_data(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Prepares the data payload specifically for the OpenAI API request.
        Merges base config, call-specific kwargs, and ensures 'model' and 'messages' are present.
        """

        # Start with base configurations stored during __init__
        data = {**self.config}

        # Override with any kwargs passed directly to get_completion

        data.update(kwargs)

        # Ensure model and messages are set, prioritizing call-time args if any, then instance defaults

        data["model"] = kwargs.get("model", self.model_name)
        data["messages"] = messages # messages are always from the direct call

        return data






