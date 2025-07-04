import json
from datetime import datetime
from src.tooling.base_tool import BaseTool
from typing import List

class GetCurrentTimeTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_current_time"
    
    @property
    def description(self) -> str:
        return "Returns the current date and time. It takes no arguments."
    
    @property
    def keywords(self) -> List[str]:
        return [
            "time", "date", "current", "now", "today",
            "timestamp", "clock", "datetime"
        ]
    
    @property
    def signature(self) -> str:
        return "get_current_time() -> datetime_string"
    
    @property
    def input_schema(self) -> dict:
        # This tool takes no arguments
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    @property
    def response_format(self) -> dict:
        return {
            "status": "string",
            "current_time": "string"
        }
    
    def execute(self, args: dict) -> str:
        # args is expected to be an empty dict, but we don't strictly need to check it
        # if the input_schema is clear and LLM follows it.
        now = datetime.now()
        current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        return json.dumps({"status": "success", "current_time": current_time_str})
