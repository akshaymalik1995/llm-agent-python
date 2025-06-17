from abc import ABC, abstractmethod

class BaseTool(ABC):
    """
    Abstract base class for all tools that the AI agent can use.
    """

    # TODO: Ask what the purpose of @property, @abstractmethod
    @property
    @abstractmethod
    def name(self) -> str:
        """
        A unique, machine-readable name for the tool.
        Example: "read_file", "execute_command"
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A detailed, human-readable description of what the tool does,
        its capabilities, and how to use it. This will be used by the LLM
        to decide when and how to use the tool.
        Include information about expected arguments.
        """
        pass

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """
        A JSON schema describing the expected input arguments for the tool.
        This helps with validation and can also be provided to the LLM.
        Example:
        {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "The path to the file."},
                "content": {"type": "string", "description": "The new content for the file."}
            },
            "required": ["file_path", "content"]
        }
        """
        pass

    @abstractmethod
    def execute(self, args: dict) -> str:
        """
        Executes the tool's action with the given arguments.

        Args:
            args: A dictionary of arguments conforming to the input_schema.

        Returns:
            A string representing the result of the tool's execution.
            This could be a success message, an error message, or data returned by the tool.
            It's often useful to return JSON formatted strings for complex outputs.
        """
        pass

    def get_tool_info(self) -> dict:
        """
        Returns a dictionary with the tool's name, description, and input schema.
        This can be provided to the LLM as part of the system prompt.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema
        }