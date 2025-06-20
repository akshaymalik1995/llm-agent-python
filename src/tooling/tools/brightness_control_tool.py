"""
# Brightness Control Tool for macOS
- Only for development and testing purposes.
"""

import subprocess
import json
from typing import List
from src.tooling.base_tool import BaseTool
from src.custom_logging import logger

DEFAULT_BRIGHTNESS_STEP = 2  # Default step for brightness adjustment
DELAY_BETWEEN_STEPS = 0.1  # Delay between key presses in seconds
COMMAND_FOR_BRIGHTNESS_INCREASE = "key code 144"  # Key code for brightness up
COMMAND_FOR_BRIGHTNESS_DECREASE = "key code 145"  # Key code for brightness down

class BrightnessControlTool(BaseTool):
    """
    Tool for controlling macOS display brightness using keyboard simulation.
    """

    @property
    def name(self) -> str:
        return "brightness_control"

    @property
    def keywords(self) -> List[str]:
        return [
            "brightness", "screen", "display", "backlight", 
            "dim", "bright", "luminosity", "monitor", "adjust"
        ]

    @property
    def signature(self) -> str:
        return "brightness_control(action: str('increase' | 'decrease'), value: int = None) -> status"

    @property
    def description(self) -> str:
        return """
        Controls the brightness of the macOS display using keyboard simulation.
        
        Actions:
        - 'increase': Increases brightness by specified steps (default 2 steps)
        - 'decrease': Decreases brightness by specified steps (default 2 steps)
        
        Value represents number of brightness steps (1-16).
        """

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["increase", "decrease"],
                    "description": "The brightness action to perform"
                },
                "value": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 16,
                    "description": "Number of brightness steps (1-16)"
                }
            },
            "required": ["action"]
        }

    def execute(self, args: dict) -> str:
        action = args.get("action")
        value = args.get("value")
        
        try:
            if action == "increase":
                steps = int(value) if value is not None else DEFAULT_BRIGHTNESS_STEP
                logger.info(f"Increasing brightness by {steps} steps")
                return self._increase_brightness(steps)
            elif action == "decrease":
                steps = int(value) if value is not None else DEFAULT_BRIGHTNESS_STEP
                return self._decrease_brightness(steps)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
                
        except Exception as e:
            return json.dumps({"error": f"Failed to control brightness: {str(e)}"})

    def _increase_brightness(self, steps: int) -> str:
        """Increase brightness by specified number of steps."""
        try:
            steps = max(1, min(16, steps)) * 2  # Each step is 2 key presses

            script = f'tell application "System Events" to repeat {steps} times \n {COMMAND_FOR_BRIGHTNESS_INCREASE} \n delay {DELAY_BETWEEN_STEPS} \n end repeat'

            logger.info(f"Running AppleScript to increase brightness by {steps} steps")
            
            subprocess.run(["osascript", "-e", script], 
                          capture_output=True, text=True, check=True)
            
            return json.dumps({
                "success": True,
                "steps": steps,
                "message": f"Brightness increased by {steps} steps"
            })
            
        except subprocess.CalledProcessError as e:
            return json.dumps({
                "error": f"Could not increase brightness: {str(e)}",
                "suggestion": "Grant accessibility permissions to Terminal in System Preferences"
            })

    def _decrease_brightness(self, steps: int) -> str:
        """Decrease brightness by specified number of steps."""
        try:
            steps = max(1, min(16, steps)) * 2  # Each step is 2 key presses
            
            script = f'tell application "System Events" to repeat {steps} times \n {COMMAND_FOR_BRIGHTNESS_DECREASE} \n delay {DELAY_BETWEEN_STEPS} \n end repeat'

            subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, check=True)

            return json.dumps({
                "success": True,
                "steps": steps,
                "message": f"Brightness decreased by {steps} steps"
            })
            
        except subprocess.CalledProcessError as e:
            return json.dumps({
                "error": f"Could not decrease brightness: {str(e)}",
                "suggestion": "Grant accessibility permissions to Terminal in System Preferences"
            })