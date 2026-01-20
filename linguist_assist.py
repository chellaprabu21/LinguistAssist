"""
LinguistAssist - A GUI automation agent using Gemini API for intelligent UI element detection.
"""

import json
import os
import re
import sys
import time
from typing import Optional, Tuple, List

import google.generativeai as genai
import pyautogui
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure pyautogui safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5


class CoordinateMapper:
    """Maps normalized coordinates (0-1000) to actual screen pixel coordinates."""
    
    def __init__(self):
        """Initialize with current screen resolution."""
        self.screen_width, self.screen_height = pyautogui.size()
    
    def normalize_to_pixels(self, normalized_y: float, normalized_x: float) -> Tuple[int, int]:
        """
        Convert normalized coordinates (0-1000 scale) to pixel coordinates.
        
        Args:
            normalized_y: Y coordinate in 0-1000 scale
            normalized_x: X coordinate in 0-1000 scale
        
        Returns:
            Tuple of (pixel_x, pixel_y) coordinates
        """
        pixel_x = int((normalized_x / 1000.0) * self.screen_width)
        pixel_y = int((normalized_y / 1000.0) * self.screen_height)
        
        # Ensure coordinates are within screen bounds
        pixel_x = max(0, min(pixel_x, self.screen_width - 1))
        pixel_y = max(0, min(pixel_y, self.screen_height - 1))
        
        return (pixel_x, pixel_y)


class LinguistAssist:
    """GUI automation agent using Gemini API for UI element detection."""
    
    SYSTEM_INSTRUCTION = (
        "You are a GUI automation agent. When given a task and a screenshot, "
        "identify the center point of the UI element required to fulfill the task. "
        "Return the coordinates in JSON format: {'point': [y, x]}. "
        "The coordinates must be normalized to a 0-1000 scale."
    )
    
    PLANNING_INSTRUCTION = (
        "You are a GUI automation planning agent. Analyze the screenshot and the overall goal. "
        "Determine: (1) Is the goal complete? (2) If not, what is the next action needed? "
        "Return JSON format: {'complete': true/false, 'action': 'description of next action', 'point': [y, x] if action needed}. "
        "If complete is true, point can be omitted. The coordinates must be normalized to a 0-1000 scale."
    )
    
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        """
        Initialize LinguistAssist.
        
        Args:
            model_name: Gemini model to use ('gemini-1.5-flash' or 'gemini-1.5-pro')
            api_key: Google Generative AI API key (if not provided, reads from GEMINI_API_KEY env var)
        """
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "API key not provided. Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        genai.configure(api_key=api_key)
        
        # Map user-friendly model names to actual API model names
        # The deprecated google.generativeai package uses different model names
        model_mapping = {
            "gemini-1.5-flash": "gemini-flash-latest",
            "gemini-1.5-pro": "gemini-pro-latest",
            "gemini-flash": "gemini-flash-latest",
            "gemini-pro": "gemini-pro-latest",
        }
        normalized_model_name = model_mapping.get(model_name, model_name)
        
        self.model = genai.GenerativeModel(
            model_name=normalized_model_name,
            system_instruction=self.SYSTEM_INSTRUCTION
        )
        # Create a planning model for goal-oriented execution
        self.planning_model = genai.GenerativeModel(
            model_name=normalized_model_name,
            system_instruction=self.PLANNING_INSTRUCTION
        )
        self.coordinate_mapper = CoordinateMapper()
        self.model_name = model_name
    
    def capture_screenshot(self) -> Image.Image:
        """
        Capture a screenshot of the current screen.
        
        Returns:
            PIL Image object of the screenshot
        
        Raises:
            RuntimeError: If screenshot capture fails (e.g., missing permissions)
        """
        try:
            screenshot = pyautogui.screenshot()
            return screenshot
        except Exception as e:
            error_msg = (
                f"Failed to capture screenshot: {e}\n\n"
                "On macOS, you may need to grant screen recording permissions:\n"
                "1. Go to System Settings > Privacy & Security > Screen Recording\n"
                "2. Enable permissions for Terminal (or your terminal app)\n"
                "3. Restart your terminal after granting permissions\n\n"
                "Alternatively, ensure you're running this in a GUI environment."
            )
            raise RuntimeError(error_msg) from e
    
    def detect_element(self, task: str, screenshot: Optional[Image.Image] = None) -> Tuple[int, int]:
        """
        Detect UI element coordinates based on task description.
        
        Args:
            task: Description of the UI element to find (e.g., "Click the login button")
            screenshot: Optional screenshot image (if None, captures a new one)
        
        Returns:
            Tuple of (pixel_x, pixel_y) coordinates
        """
        if screenshot is None:
            screenshot = self.capture_screenshot()
        
        print(f"\n[LinguistAssist] Analyzing screenshot with {self.model_name}...")
        print(f"[LinguistAssist] Task: {task}")
        
        try:
            # Send image and task to Gemini
            response = self.model.generate_content([
                f"Task: {task}",
                screenshot
            ])
            
            # Parse the response
            response_text = response.text.strip()
            print(f"[LinguistAssist] Raw response: {response_text}")
            
            # Try to extract JSON from the response
            # Handle cases where response might be wrapped in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Try to find JSON object in the text (handles cases where JSON is embedded in text)
            json_pattern = r'\{[^{}]*"point"[^{}]*\[[^\]]+\][^{}]*\}'
            json_match = re.search(json_pattern, response_text)
            if json_match:
                response_text = json_match.group(0)
            
            # Also try with single quotes (Python dict format)
            if not json_match:
                json_pattern_single = r"\{[^{}]*'point'[^{}]*\[[^\]]+\][^{}]*\}"
                json_match = re.search(json_pattern_single, response_text)
                if json_match:
                    # Convert single quotes to double quotes for JSON parsing
                    response_text = json_match.group(0).replace("'", '"')
            
            # Parse JSON
            data = json.loads(response_text)
            
            if "point" not in data:
                raise ValueError("Response does not contain 'point' key")
            
            normalized_coords = data["point"]
            if len(normalized_coords) != 2:
                raise ValueError("Point must contain exactly 2 coordinates [y, x]")
            
            normalized_y, normalized_x = normalized_coords
            
            # Convert to pixel coordinates
            pixel_x, pixel_y = self.coordinate_mapper.normalize_to_pixels(
                normalized_y, normalized_x
            )
            
            print(f"[LinguistAssist] Detected normalized coordinates: [y={normalized_y}, x={normalized_x}]")
            print(f"[LinguistAssist] Screen resolution: {self.coordinate_mapper.screen_width}x{self.coordinate_mapper.screen_height}")
            print(f"[LinguistAssist] Pixel coordinates: ({pixel_x}, {pixel_y})")
            
            return (pixel_x, pixel_y)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response_text}")
        except Exception as e:
            raise RuntimeError(f"Error during element detection: {e}")
    
    def click_element(self, task: str, screenshot: Optional[Image.Image] = None, 
                     require_confirmation: bool = False) -> bool:
        """
        Detect and click on a UI element based on task description.
        
        Args:
            task: Description of the UI element to click
            screenshot: Optional screenshot image (if None, captures a new one)
            require_confirmation: If True, wait for user confirmation before clicking (default: False)
        
        Returns:
            True if click was executed, False if cancelled
        """
        try:
            pixel_x, pixel_y = self.detect_element(task, screenshot)
            
            # Optional confirmation prompt
            if require_confirmation:
                print(f"\n[LinguistAssist] Ready to click at coordinates: ({pixel_x}, {pixel_y})")
                user_input = input("Press Enter to click, or type 'cancel' to abort: ").strip().lower()
                
                if user_input == "cancel":
                    print("[LinguistAssist] Click cancelled by user.")
                    return False
            
            # Execute click
            print(f"[LinguistAssist] Clicking at ({pixel_x}, {pixel_y})...")
            pyautogui.click(pixel_x, pixel_y)
            print("[LinguistAssist] Click executed successfully!")
            
            return True
            
        except Exception as e:
            print(f"[LinguistAssist] Error: {e}")
            return False
    
    def execute_task(self, goal: str, max_steps: int = 20):
        """
        Execute a high-level goal autonomously by analyzing the screen and taking actions.
        Takes fresh screenshots after each action and continues until the goal is achieved.
        
        Args:
            goal: High-level description of what to accomplish (e.g., "Log in to the website")
            max_steps: Maximum number of actions to take before stopping (default: 20)
        
        Returns:
            True if goal was achieved, False otherwise
        """
        print(f"[LinguistAssist] Goal: {goal}")
        print(f"[LinguistAssist] Starting autonomous execution (max {max_steps} steps)...\n")
        
        step_count = 0
        action_history = []
        
        while step_count < max_steps:
            try:
                # Take a fresh screenshot
                screenshot = self.capture_screenshot()
                step_count += 1
                
                print(f"\n[LinguistAssist] Step {step_count}: Analyzing screen...")
                
                # Use planning model to determine next action
                planning_prompt = f"Goal: {goal}\n\nAction history so far: {', '.join(action_history) if action_history else 'None'}\n\nAnalyze the current screen state and determine the next action."
                
                response = self.planning_model.generate_content([
                    planning_prompt,
                    screenshot
                ])
                
                response_text = response.text.strip()
                print(f"[LinguistAssist] Planning response: {response_text}")
                
                # Extract JSON from response
                json_pattern = r'\{[^{}]*(?:"complete"|"action"|"point")[^{}]*\}'
                json_match = re.search(json_pattern, response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)
                
                # Also try with single quotes
                if not json_match:
                    json_pattern_single = r"\{[^{}]*(?:'complete'|'action'|'point')[^{}]*\}"
                    json_match = re.search(json_pattern_single, response_text, re.DOTALL)
                    if json_match:
                        response_text = json_match.group(0).replace("'", '"')
                
                # Try to parse JSON directly first
                plan_data = None
                try:
                    plan_data = json.loads(response_text)
                except json.JSONDecodeError:
                    # If parsing fails due to unescaped quotes, extract values manually
                    print(f"[LinguistAssist] JSON parse error, extracting values manually...")
                    
                    # Extract complete
                    complete_match = re.search(r'"complete"\s*:\s*(true|false)', response_text, re.IGNORECASE)
                    
                    # Extract action - find "action": " and then find the value until we hit ", "point" or end
                    # Look for "action": " then capture until we see ", "point" or end of string
                    action_start = response_text.find('"action": "')
                    if action_start != -1:
                        action_start += len('"action": "')
                        # Find the end - look for ", "point" or end of object
                        point_start = response_text.find(', "point"', action_start)
                        if point_start == -1:
                            point_start = response_text.find('", "point"', action_start)
                        if point_start != -1:
                            action_value = response_text[action_start:point_start].strip()
                            # Remove trailing quote if present
                            if action_value.endswith('"'):
                                action_value = action_value[:-1]
                            # Remove any unescaped quotes from the action value
                            action_value = action_value.replace('"', '')
                        else:
                            action_value = ""
                    else:
                        action_value = ""
                    
                    # Extract point
                    point_match = re.search(r'"point"\s*:\s*\[(\d+),\s*(\d+)\]', response_text)
                    
                    if complete_match and action_value and point_match:
                        plan_data = {
                            "complete": complete_match.group(1).lower() == "true",
                            "action": action_value,
                            "point": [int(point_match.group(1)), int(point_match.group(2))]
                        }
                    else:
                        raise ValueError(f"Failed to parse planning response. Complete: {complete_match is not None}, Action: {bool(action_value)}, Point: {point_match is not None}")
                
                # Check if goal is complete
                if plan_data.get("complete", False):
                    print(f"\n[LinguistAssist] ✓ Goal achieved! Completed in {step_count} steps.")
                    return True
                
                # Get next action
                action = plan_data.get("action", "")
                if not action:
                    print("[LinguistAssist] No action specified. Goal may be complete or unclear.")
                    return False
                
                print(f"[LinguistAssist] Next action: {action}")
                
                # Get coordinates for the action
                if "point" in plan_data:
                    normalized_coords = plan_data["point"]
                    if len(normalized_coords) == 2:
                        normalized_y, normalized_x = normalized_coords
                        pixel_x, pixel_y = self.coordinate_mapper.normalize_to_pixels(
                            normalized_y, normalized_x
                        )
                        
                        print(f"[LinguistAssist] Clicking at ({pixel_x}, {pixel_y})...")
                        pyautogui.click(pixel_x, pixel_y)
                        print(f"[LinguistAssist] Action executed: {action}")
                        action_history.append(action)
                        
                        # Small delay to allow UI to update
                        time.sleep(1)
                    else:
                        print(f"[LinguistAssist] Invalid coordinates format. Skipping action.")
                else:
                    # If no coordinates, try to detect them using the action description
                    print(f"[LinguistAssist] No coordinates provided. Detecting element for: {action}")
                    try:
                        pixel_x, pixel_y = self.detect_element(action, screenshot)
                        print(f"[LinguistAssist] Clicking at ({pixel_x}, {pixel_y})...")
                        pyautogui.click(pixel_x, pixel_y)
                        print(f"[LinguistAssist] Action executed: {action}")
                        action_history.append(action)
                        
                        # Small delay to allow UI to update
                        time.sleep(1)
                    except Exception as e:
                        print(f"[LinguistAssist] Failed to detect element: {e}")
                        return False
                
            except json.JSONDecodeError as e:
                print(f"[LinguistAssist] Failed to parse planning response: {e}")
                print(f"[LinguistAssist] Response was: {response_text}")
                return False
            except KeyboardInterrupt:
                print("\n[LinguistAssist] Interrupted by user.")
                return False
            except Exception as e:
                print(f"[LinguistAssist] Error during execution: {e}")
                return False
        
        print(f"\n[LinguistAssist] Reached maximum steps ({max_steps}). Goal may not be complete.")
        return False


def main():
    """Main entry point for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LinguistAssist - GUI automation agent using Gemini API"
    )
    parser.add_argument(
        "goal",
        help="High-level goal to accomplish (e.g., 'Log in to the website', 'Fill out the form and submit it')"
    )
    parser.add_argument(
        "--model",
        choices=["gemini-1.5-flash", "gemini-1.5-pro"],
        default="gemini-1.5-flash",
        help="Gemini model to use (default: gemini-1.5-flash)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum number of actions to take (default: 20)"
    )
    
    args = parser.parse_args()
    
    try:
        agent = LinguistAssist(model_name=args.model)
        agent.execute_task(args.goal, max_steps=args.max_steps)
    except KeyboardInterrupt:
        print("\n[LinguistAssist] Interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"[LinguistAssist] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
