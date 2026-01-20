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
        self.logical_width, self.logical_height = pyautogui.size()
        print(f"[CoordinateMapper] Logical screen resolution: {self.logical_width}x{self.logical_height}")
    
    def normalize_to_pixels(self, normalized_y: float, normalized_x: float, 
                            screenshot_width: Optional[int] = None, 
                            screenshot_height: Optional[int] = None) -> Tuple[int, int]:
        """
        Convert normalized coordinates (0-1000 scale) to pixel coordinates.
        
        On macOS Retina displays, screenshots are captured at higher resolution than
        the logical screen size. pyautogui.click() expects LOGICAL coordinates,
        so we must scale down from screenshot (physical) coordinates to logical coordinates.
        
        Args:
            normalized_y: Y coordinate in 0-1000 scale (based on screenshot)
            normalized_x: X coordinate in 0-1000 scale (based on screenshot)
            screenshot_width: Width of the screenshot image (if None, uses logical width)
            screenshot_height: Height of the screenshot image (if None, uses logical height)
        
        Returns:
            Tuple of (pixel_x, pixel_y) coordinates in logical screen space
        """
        # Validate normalized coordinates
        if not (0 <= normalized_x <= 1000):
            print(f"[CoordinateMapper] Warning: normalized_x {normalized_x} out of range [0-1000], clamping")
            normalized_x = max(0, min(normalized_x, 1000))
        if not (0 <= normalized_y <= 1000):
            print(f"[CoordinateMapper] Warning: normalized_y {normalized_y} out of range [0-1000], clamping")
            normalized_y = max(0, min(normalized_y, 1000))
        
        # Use screenshot dimensions if provided, otherwise use logical screen size
        if screenshot_width is None:
            screenshot_width = self.logical_width
        if screenshot_height is None:
            screenshot_height = self.logical_height
        
        # Convert normalized coordinates to screenshot pixel coordinates
        screenshot_x = (normalized_x / 1000.0) * screenshot_width
        screenshot_y = (normalized_y / 1000.0) * screenshot_height
        
        # Calculate scale factor (screenshot is usually 2x on Retina displays)
        scale_x = screenshot_width / self.logical_width if self.logical_width > 0 else 1.0
        scale_y = screenshot_height / self.logical_height if self.logical_height > 0 else 1.0
        
        # Convert from screenshot (physical) coordinates to logical screen coordinates
        # pyautogui.click() expects LOGICAL coordinates, not physical pixel coordinates!
        pixel_x = int(screenshot_x / scale_x)
        pixel_y = int(screenshot_y / scale_y)
        
        # Ensure coordinates are within logical screen bounds
        pixel_x = max(0, min(pixel_x, self.logical_width - 1))
        pixel_y = max(0, min(pixel_y, self.logical_height - 1))
        
        print(f"[CoordinateMapper] Mapped ({normalized_x:.1f}, {normalized_y:.1f}) -> screenshot ({screenshot_x:.1f}, {screenshot_y:.1f}) -> logical ({pixel_x}, {pixel_y}) [scale: {scale_x:.2f}x]")
        
        return (pixel_x, pixel_y)


class LinguistAssist:
    """GUI automation agent using Gemini API for UI element detection."""
    
    SYSTEM_INSTRUCTION = (
        "You are a GUI automation agent. When given a task and a screenshot, "
        "identify the center point of the UI element required to fulfill the task. "
        "Return ONLY valid JSON format: {\"point\": [y, x]}. "
        "The coordinates must be normalized to a 0-1000 scale where: "
        "- x=0 is the left edge, x=1000 is the right edge "
        "- y=0 is the top edge, y=1000 is the bottom edge "
        "Return ONLY the JSON object, no additional text or explanation. "
        "The point array must contain exactly 2 numbers: [y, x] in that order."
    )
    
    PLANNING_INSTRUCTION = (
        "You are a GUI automation planning agent. Analyze the screenshot and the overall goal. "
        "Determine: (1) Is the goal complete? (2) If not, what is the next SINGLE action needed? "
        "CRITICAL: Before suggesting the same action again, verify if the previous action succeeded by checking the current screen state. "
        "If you see the conversation is already open with the correct person, move to the next step (clicking the message field or typing). "
        "Actions can be: 'click' (click on an element), 'type' (type text into a field), 'press_key' (press a keyboard key like Enter, Tab, Escape). "
        "Return JSON format: {'complete': true/false, 'action_type': 'click'|'type'|'press_key', 'action': 'description of what you're doing', 'point': [y, x] if click/type needs coordinates, 'text': 'text to type' if type action, 'key': 'key name' if press_key}. "
        "If complete is true, other fields can be omitted. The coordinates must be normalized to a 0-1000 scale. "
        "IMPORTANT: Set 'complete': true if the goal is achieved. For 'open app' goals, if you see the app window open or the app is visible on screen, the goal is complete. "
        "If you've clicked the same element multiple times without progress, consider if the goal might already be achieved. "
        "IMPORTANT: Break down complex tasks into individual steps. For 'send message to X': "
        "(1) First step: click on the contact in the DM list (ONLY if their conversation is not already open), "
        "(2) Second step: verify the conversation is open (check if you see their name in the header), "
        "(3) Third step: click in the message input field at the bottom, "
        "(4) Fourth step: type the message (action_type='type', provide text field), "
        "(5) Fifth step: send the message (action_type='press_key', key='enter' or click send button). "
        "Only return ONE action per response. After each action, a new screenshot will be taken for the next step. "
        "DO NOT repeat the same action if the screen shows it has already succeeded - move to the next step instead."
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
        Tries screenshot service first, then falls back to direct methods.
        
        Returns:
            PIL Image object of the screenshot
        
        Raises:
            RuntimeError: If screenshot capture fails (e.g., missing permissions)
        """
        # Try screenshot service first (for Launch Agent compatibility)
        try:
            import requests
            import base64
            import io
            
            response = requests.get("http://127.0.0.1:8081/screenshot", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    img_base64 = data.get("image")
                    img_data = base64.b64decode(img_base64)
                    screenshot = Image.open(io.BytesIO(img_data))
                    print("[LinguistAssist] Screenshot captured via screenshot service")
                    return screenshot
                else:
                    print(f"[LinguistAssist] Screenshot service error: {data.get('error')}")
            else:
                print(f"[LinguistAssist] Screenshot service returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[LinguistAssist] Screenshot service not available: {e}")
        except Exception as e:
            print(f"[LinguistAssist] Screenshot service error: {e}")
        
        # Fallback to direct screenshot methods
        try:
            # Try pyautogui first (works in terminal/interactive sessions)
            screenshot = pyautogui.screenshot()
            return screenshot
        except Exception as e:
            # Fallback to screencapture command (works better in Launch Agents)
            try:
                import subprocess
                import tempfile
                
                # Use macOS screencapture command
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_file.close()
                
                result = subprocess.run(
                    ['screencapture', '-x', temp_file.name],
                    capture_output=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    screenshot = Image.open(temp_file.name)
                    os.unlink(temp_file.name)
                    return screenshot
                else:
                    os.unlink(temp_file.name)
                    raise RuntimeError(f"screencapture failed: {result.stderr.decode()}")
            except Exception as fallback_error:
                error_msg = (
                    f"Failed to capture screenshot: {e}\n"
                    f"Fallback also failed: {fallback_error}\n\n"
                    "On macOS, you may need to grant screen recording permissions:\n"
                    "1. Go to System Settings > Privacy & Security > Screen Recording\n"
                    "2. Enable permissions for Python.app (or Python 3.12)\n"
                    "3. Restart the service after granting permissions\n\n"
                    "Alternatively, ensure you're running this in a GUI environment."
                )
                raise RuntimeError(error_msg) from e
    
    def _extract_json_from_response(self, response_text: str) -> dict:
        """
        Robustly extract JSON from response text, handling various formats.
        
        Args:
            response_text: Raw response text from Gemini
        
        Returns:
            Parsed JSON dictionary
        """
        original_text = response_text.strip()
        
        # Strategy 1: Try direct JSON parse first
        try:
            return json.loads(original_text)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract from markdown code blocks
        if "```json" in original_text:
            json_start = original_text.find("```json") + 7
            json_end = original_text.find("```", json_start)
            if json_end != -1:
                try:
                    return json.loads(original_text[json_start:json_end].strip())
                except json.JSONDecodeError:
                    pass
        
        if "```" in original_text:
            json_start = original_text.find("```") + 3
            json_end = original_text.find("```", json_start)
            if json_end != -1:
                try:
                    return json.loads(original_text[json_start:json_end].strip())
                except json.JSONDecodeError:
                    pass
        
        # Strategy 3: Find JSON object with balanced braces
        brace_start = original_text.find('{')
        if brace_start != -1:
            brace_count = 0
            brace_end = -1
            for i in range(brace_start, len(original_text)):
                if original_text[i] == '{':
                    brace_count += 1
                elif original_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        brace_end = i + 1
                        break
            
            if brace_end != -1:
                json_candidate = original_text[brace_start:brace_end]
                try:
                    return json.loads(json_candidate)
                except json.JSONDecodeError:
                    pass
        
        # Strategy 4: Use regex to find JSON-like structures
        # Match: {"point": [number, number]} or {'point': [number, number]}
        json_patterns = [
            r'\{[^{}]*"point"\s*:\s*\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\][^{}]*\}',
            r"\{[^{}]*'point'\s*:\s*\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\][^{}]*\}",
            r'\{[^{}]*point[^{}]*\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\][^{}]*\}',
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, original_text, re.IGNORECASE)
            if match:
                try:
                    y_val = float(match.group(1))
                    x_val = float(match.group(2))
                    return {"point": [y_val, x_val]}
                except (ValueError, IndexError):
                    continue
        
        # Strategy 5: Try to extract coordinates directly using regex
        # Look for [number, number] pattern that might be coordinates
        coord_pattern = r'\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]'
        coord_match = re.search(coord_pattern, original_text)
        if coord_match:
            try:
                y_val = float(coord_match.group(1))
                x_val = float(coord_match.group(2))
                # Validate they're in reasonable range (0-1000)
                if 0 <= y_val <= 1000 and 0 <= x_val <= 1000:
                    return {"point": [y_val, x_val]}
            except (ValueError, IndexError):
                pass
        
        raise ValueError(f"Could not extract valid JSON from response: {original_text[:200]}")
    
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
        
        screenshot_width, screenshot_height = screenshot.size
        print(f"\n[LinguistAssist] Analyzing screenshot with {self.model_name}...")
        print(f"[LinguistAssist] Task: {task}")
        print(f"[LinguistAssist] Screenshot dimensions: {screenshot_width}x{screenshot_height}")
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Send image and task to Gemini
                response = self.model.generate_content([
                    f"Task: {task}",
                    screenshot
                ])
                
                # Parse the response
                response_text = response.text.strip()
                print(f"[LinguistAssist] Raw response: {response_text}")
                
                # Extract JSON using robust method
                data = self._extract_json_from_response(response_text)
                
                if "point" not in data:
                    raise ValueError("Response does not contain 'point' key")
                
                normalized_coords = data["point"]
                if not isinstance(normalized_coords, (list, tuple)) or len(normalized_coords) != 2:
                    raise ValueError(f"Point must be a list/tuple with exactly 2 coordinates, got: {normalized_coords}")
                
                normalized_y, normalized_x = float(normalized_coords[0]), float(normalized_coords[1])
                
                # Validate normalized coordinates
                if not (0 <= normalized_x <= 1000 and 0 <= normalized_y <= 1000):
                    print(f"[LinguistAssist] Warning: Coordinates out of range: x={normalized_x}, y={normalized_y}")
                    if attempt < max_retries - 1:
                        print(f"[LinguistAssist] Retrying... (attempt {attempt + 1}/{max_retries})")
                        continue
                
                # Convert to pixel coordinates using screenshot dimensions
                pixel_x, pixel_y = self.coordinate_mapper.normalize_to_pixels(
                    normalized_y, normalized_x, screenshot_width, screenshot_height
                )
                
                print(f"[LinguistAssist] Detected normalized coordinates: [y={normalized_y:.2f}, x={normalized_x:.2f}]")
                print(f"[LinguistAssist] Logical screen resolution: {self.coordinate_mapper.logical_width}x{self.coordinate_mapper.logical_height}")
                print(f"[LinguistAssist] Pixel coordinates: ({pixel_x}, {pixel_y})")
                
                return (pixel_x, pixel_y)
                
            except (json.JSONDecodeError, ValueError) as e:
                if attempt < max_retries - 1:
                    print(f"[LinguistAssist] Parse error, retrying... (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.5)  # Brief delay before retry
                    continue
                else:
                    raise ValueError(f"Failed to parse JSON response after {max_retries} attempts: {e}\nResponse: {response_text[:500]}")
            except Exception as e:
                raise RuntimeError(f"Error during element detection: {e}")
        
        raise RuntimeError(f"Failed to detect element after {max_retries} attempts")
    
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
        recent_actions = []  # Track recent actions to detect loops
        recent_coordinates = []  # Track recent coordinates to detect loops
        loop_count = 0  # Track consecutive loop detections
        
        while step_count < max_steps:
            try:
                # Take a fresh screenshot
                screenshot = self.capture_screenshot()
                screenshot_width, screenshot_height = screenshot.size
                step_count += 1
                
                print(f"\n[LinguistAssist] Step {step_count}: Analyzing screen...")
                print(f"[LinguistAssist] Screenshot dimensions: {screenshot_width}x{screenshot_height}")
                
                # Build planning prompt with loop awareness
                planning_prompt = f"Goal: {goal}\n\n"
                
                if action_history:
                    planning_prompt += f"Action history so far: {', '.join(action_history[-5:])}\n\n"
                
                # Add loop detection warning to prompt
                if len(recent_actions) >= 3:
                    last_three = recent_actions[-3:]
                    if len(set([a.lower() for a in last_three])) <= 1:  # All same action
                        planning_prompt += "⚠️ WARNING: The same action has been repeated multiple times. "
                        planning_prompt += "Please carefully check if the goal is already achieved. "
                        planning_prompt += "If the app is already open or the task is complete, set 'complete': true. "
                        planning_prompt += "If not, try a different approach or action.\n\n"
                        loop_count += 1
                    else:
                        loop_count = 0  # Reset if actions differ
                
                # If stuck in loop for too long, ask Gemini to reconsider completion
                if loop_count >= 3:
                    planning_prompt += "⚠️ CRITICAL: Multiple repeated actions detected. "
                    planning_prompt += f"Please verify if the goal '{goal}' is actually complete. "
                    planning_prompt += "Look for visual indicators that the task succeeded (e.g., app window open, button clicked, etc.). "
                    planning_prompt += "If the goal appears achieved, set 'complete': true immediately.\n\n"
                
                planning_prompt += "Analyze the current screen state and determine the next action."
                
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
                    
                    # Extract action_type
                    action_type_match = re.search(r'"action_type"\s*:\s*"(click|type|press_key)"', response_text, re.IGNORECASE)
                    action_type = action_type_match.group(1).lower() if action_type_match else "click"
                    
                    # Extract action description
                    action_value = ""
                    action_start = response_text.find('"action": "')
                    if action_start != -1:
                        action_start += len('"action": "')
                        # Find the end - look for ", "point", ", "text", ", "key" or end of object
                        end_markers = [', "point"', '", "point"', ', "text"', '", "text"', ', "key"', '", "key"', ', "action_type"', '", "action_type"']
                        point_start = None
                        for marker in end_markers:
                            pos = response_text.find(marker, action_start)
                            if pos != -1 and (point_start is None or pos < point_start):
                                point_start = pos
                        if point_start != -1:
                            action_value = response_text[action_start:point_start].strip()
                            if action_value.endswith('"'):
                                action_value = action_value[:-1]
                            action_value = action_value.replace('"', '')
                    
                    # Extract text (for type actions)
                    text_value = ""
                    text_match = re.search(r'"text"\s*:\s*"([^"]*(?:"[^"]*)*)"', response_text)
                    if text_match:
                        text_value = text_match.group(1).replace('"', '')
                    
                    # Extract key (for press_key actions)
                    key_value = ""
                    key_match = re.search(r'"key"\s*:\s*"([^"]+)"', response_text)
                    if key_match:
                        key_value = key_match.group(1)
                    
                    # Extract point - handle both integer and float coordinates
                    point_patterns = [
                        r'"point"\s*:\s*\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]',
                        r"'point'\s*:\s*\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]",
                    ]
                    point_match = None
                    for pattern in point_patterns:
                        point_match = re.search(pattern, response_text)
                        if point_match:
                            break
                    
                    if complete_match:
                        plan_data = {
                            "complete": complete_match.group(1).lower() == "true",
                            "action_type": action_type,
                        }
                        if action_value:
                            plan_data["action"] = action_value
                        if text_value:
                            plan_data["text"] = text_value
                        if key_value:
                            plan_data["key"] = key_value
                        if point_match:
                            try:
                                y_val = float(point_match.group(1))
                                x_val = float(point_match.group(2))
                                # Validate coordinates are in range
                                if 0 <= y_val <= 1000 and 0 <= x_val <= 1000:
                                    plan_data["point"] = [y_val, x_val]
                                else:
                                    print(f"[LinguistAssist] Warning: Coordinates out of range: y={y_val}, x={x_val}")
                            except (ValueError, IndexError) as e:
                                print(f"[LinguistAssist] Warning: Could not parse point coordinates: {e}")
                    else:
                        raise ValueError(f"Failed to parse planning response. Could not extract required fields.")
                
                # Check if goal is complete
                if plan_data.get("complete", False):
                    print(f"\n[LinguistAssist] ✓ Goal achieved! Completed in {step_count} steps.")
                    return True
                
                # If we've been in a loop for too long and Gemini still says not complete, 
                # but keeps suggesting the same action, fail gracefully
                if loop_count >= 4:
                    print(f"\n[LinguistAssist] Error: Stuck in loop for {loop_count} steps. Task may be impossible or already complete.")
                    print(f"[LinguistAssist] Recent actions: {recent_actions[-5:]}")
                    return False
                
                # Get action type and details
                action_type = plan_data.get("action_type", "click")  # Default to click for backward compatibility
                action = plan_data.get("action", "")
                text_to_type = plan_data.get("text", "")
                key_to_press = plan_data.get("key", "")
                
                if not action and not text_to_type and not key_to_press:
                    print("[LinguistAssist] No action specified. Goal may be complete or unclear.")
                    return False
                
                print(f"[LinguistAssist] Action type: {action_type}")
                if action:
                    print(f"[LinguistAssist] Action: {action}")
                if text_to_type:
                    print(f"[LinguistAssist] Text to type: {text_to_type}")
                if key_to_press:
                    print(f"[LinguistAssist] Key to press: {key_to_press}")
                
                # Execute based on action type
                if action_type == "type":
                    # Type text - first click on the field if coordinates provided or action describes the field
                    if "point" in plan_data:
                        normalized_coords = plan_data["point"]
                        if len(normalized_coords) == 2:
                            normalized_y, normalized_x = float(normalized_coords[0]), float(normalized_coords[1])
                            pixel_x, pixel_y = self.coordinate_mapper.normalize_to_pixels(
                                normalized_y, normalized_x, screenshot_width, screenshot_height
                            )
                            print(f"[LinguistAssist] Clicking on input field at ({pixel_x}, {pixel_y})...")
                            # Try GUI action service first
                            try:
                                import requests
                                response = requests.post(
                                    "http://127.0.0.1:8081/click",
                                    json={"x": pixel_x, "y": pixel_y},
                                    timeout=2
                                )
                                if not (response.status_code == 200 and response.json().get("success")):
                                    pyautogui.click(pixel_x, pixel_y)
                            except Exception:
                                pyautogui.click(pixel_x, pixel_y)
                            time.sleep(0.3)  # Brief delay for field to focus
                    elif action:
                        # Try to detect the input field from action description
                        try:
                            pixel_x, pixel_y = self.detect_element(action, screenshot)
                            print(f"[LinguistAssist] Clicking on input field at ({pixel_x}, {pixel_y})...")
                            pyautogui.click(pixel_x, pixel_y)
                            time.sleep(0.3)
                        except Exception as e:
                            print(f"[LinguistAssist] Could not locate input field, trying to type anyway: {e}")
                    
                    # Type the text
                    if text_to_type:
                        print(f"[LinguistAssist] Typing: {text_to_type}")
                        # Try GUI action service first
                        try:
                            import requests
                            response = requests.post(
                                "http://127.0.0.1:8081/type",
                                json={"text": text_to_type, "interval": 0.05},
                                timeout=5
                            )
                            if not (response.status_code == 200 and response.json().get("success")):
                                pyautogui.write(text_to_type, interval=0.05)
                        except Exception:
                            pyautogui.write(text_to_type, interval=0.05)
                        action_history.append(f"Typed: {text_to_type}")
                    else:
                        print("[LinguistAssist] No text provided for type action.")
                        return False
                    
                    time.sleep(0.5)  # Delay after typing
                    
                elif action_type == "press_key":
                    # Press a keyboard key
                    if key_to_press:
                        key_name = key_to_press.lower()
                        print(f"[LinguistAssist] Pressing key: {key_name}")
                        
                        # Map common key names to pyautogui key names
                        key_mapping = {
                            "enter": "return",
                            "return": "return",
                            "tab": "tab",
                            "escape": "esc",
                            "esc": "esc",
                            "space": "space",
                            "backspace": "backspace",
                            "delete": "delete",
                        }
                        
                        pyautogui_key = key_mapping.get(key_name, key_name)
                        # Try GUI action service first
                        try:
                            import requests
                            response = requests.post(
                                "http://127.0.0.1:8081/press_key",
                                json={"key": key_name},
                                timeout=2
                            )
                            if not (response.status_code == 200 and response.json().get("success")):
                                pyautogui.press(pyautogui_key)
                        except Exception:
                            pyautogui.press(pyautogui_key)
                        action_history.append(f"Pressed key: {key_name}")
                        time.sleep(0.5)
                    else:
                        print("[LinguistAssist] No key specified for press_key action.")
                        return False
                        
                else:  # Default: click action
                    # Get coordinates for the click action
                    if "point" in plan_data:
                        normalized_coords = plan_data["point"]
                        if len(normalized_coords) == 2:
                            normalized_y, normalized_x = float(normalized_coords[0]), float(normalized_coords[1])
                            pixel_x, pixel_y = self.coordinate_mapper.normalize_to_pixels(
                                normalized_y, normalized_x, screenshot_width, screenshot_height
                            )
                            
                            # Check for loops: if we've clicked near this location recently, skip or try different approach
                            is_repeat = False
                            for prev_coords in recent_coordinates[-3:]:  # Check last 3 actions
                                if prev_coords:
                                    prev_x, prev_y = prev_coords
                                    # If coordinates are very close (within 50 pixels), it's likely a repeat
                                    if abs(pixel_x - prev_x) < 50 and abs(pixel_y - prev_y) < 50:
                                        is_repeat = True
                                        break
                            
                            # Check if we're repeating the same action
                            if len(recent_actions) >= 2 and action.lower() in [a.lower() for a in recent_actions[-2:]]:
                                print(f"[LinguistAssist] Warning: Detected potential loop - same action repeated")
                                print(f"[LinguistAssist] Recent actions: {recent_actions[-3:]}")
                                
                                # If we've repeated the same action 3+ times, fail faster
                                if len(recent_actions) >= 3:
                                    last_three_actions = [a.lower() for a in recent_actions[-3:]]
                                    if len(set(last_three_actions)) == 1:  # All identical
                                        print(f"[LinguistAssist] Error: Stuck in loop - same action repeated 3+ times")
                                        print(f"[LinguistAssist] Failing task to prevent infinite loop")
                                        return False
                                
                                # Try a slightly different coordinate or wait longer
                                if is_repeat:
                                    print(f"[LinguistAssist] Coordinates are very similar to recent clicks. Waiting longer and trying again...")
                                    time.sleep(2)  # Longer wait
                            
                            # Add small random offset to improve click accuracy (within 3 pixels)
                            import random
                            offset_x = random.randint(-3, 3)
                            offset_y = random.randint(-3, 3)
                            click_x = max(0, min(pixel_x + offset_x, self.coordinate_mapper.logical_width - 1))
                            click_y = max(0, min(pixel_y + offset_y, self.coordinate_mapper.logical_height - 1))
                            
                            print(f"[LinguistAssist] Clicking at ({click_x}, {click_y}) (mapped from normalized {normalized_x:.1f}, {normalized_y:.1f})...")
                            
                            # Try GUI action service first (for Launch Agent compatibility)
                            try:
                                import requests
                                response = requests.post(
                                    "http://127.0.0.1:8081/click",
                                    json={"x": click_x, "y": click_y},
                                    timeout=2
                                )
                                if response.status_code == 200 and response.json().get("success"):
                                    print(f"[LinguistAssist] Click executed via GUI service")
                                else:
                                    # Fallback to direct pyautogui with slight delay for better accuracy
                                    time.sleep(0.1)
                                    pyautogui.click(click_x, click_y)
                            except Exception:
                                # Fallback to direct pyautogui with slight delay for better accuracy
                                time.sleep(0.1)
                                pyautogui.click(click_x, click_y)
                            
                            # Wait a bit for the click to register
                            time.sleep(0.3)
                            
                            print(f"[LinguistAssist] Action executed: {action}")
                            action_history.append(action)
                            recent_actions.append(action)
                            recent_coordinates.append((pixel_x, pixel_y))
                            
                            # Keep only last 5 actions/coordinates
                            if len(recent_actions) > 5:
                                recent_actions.pop(0)
                            if len(recent_coordinates) > 5:
                                recent_coordinates.pop(0)
                            
                            # Delay to allow UI to update and verify action took effect
                            time.sleep(2.0)  # Increased delay for UI to update and verify
                        else:
                            print(f"[LinguistAssist] Invalid coordinates format. Skipping action.")
                    else:
                        # If no coordinates, try to detect them using the action description
                        if action:
                            print(f"[LinguistAssist] No coordinates provided. Detecting element for: {action}")
                            try:
                                pixel_x, pixel_y = self.detect_element(action, screenshot)
                                print(f"[LinguistAssist] Clicking at ({pixel_x}, {pixel_y})...")
                                # Try GUI action service first
                                try:
                                    import requests
                                    response = requests.post(
                                        "http://127.0.0.1:8081/click",
                                        json={"x": pixel_x, "y": pixel_y},
                                        timeout=2
                                    )
                                    if not (response.status_code == 200 and response.json().get("success")):
                                        pyautogui.click(pixel_x, pixel_y)
                                except Exception:
                                    pyautogui.click(pixel_x, pixel_y)
                                print(f"[LinguistAssist] Action executed: {action}")
                                action_history.append(action)
                                
                                # Small delay to allow UI to update
                                time.sleep(1)
                            except Exception as e:
                                print(f"[LinguistAssist] Failed to detect element: {e}")
                                return False
                        else:
                            print("[LinguistAssist] No action or coordinates provided.")
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
