# LinguistAssist

A GUI automation agent that uses Google's Gemini API to intelligently detect and interact with UI elements based on natural language descriptions.

## Features

- **Intelligent UI Detection**: Uses Gemini AI to identify UI elements from screenshots
- **Natural Language Tasks**: Describe what you want to click in plain English
- **Safety First**: Prompts for confirmation before executing clicks
- **Flexible Models**: Choose between `gemini-1.5-flash` (fast, maps to `gemini-flash-latest`) or `gemini-1.5-pro` (complex UIs, maps to `gemini-pro-latest`)
- **Coordinate Mapping**: Automatically converts normalized coordinates to your screen resolution

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Gemini API key:
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a `.env` file in the project root:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

### Command Line

Run with a high-level goal. The agent will analyze the screen and execute steps autonomously:

```bash
python3 linguist_assist.py "Log in to the website"
```

The agent will:
- Analyze the current screen
- Determine what action to take
- Execute the action
- Take a fresh screenshot
- Continue until the goal is achieved

Use a different model for complex UIs:
```bash
python3 linguist_assist.py "Fill out the form and submit it" --model gemini-1.5-pro
```

Set maximum steps:
```bash
python3 linguist_assist.py "Complete the checkout process" --max-steps 30
```

### Python API

```python
from linguist_assist import LinguistAssist

# Initialize the agent
agent = LinguistAssist(model_name="gemini-1.5-flash")

# Execute a high-level goal autonomously
agent.execute_task("Log in to the website")

# Set maximum steps for complex workflows
agent.execute_task("Complete the checkout process", max_steps=30)

# Or just detect coordinates without clicking
x, y = agent.detect_element("Find the search bar")
print(f"Element is at: ({x}, {y})")

# Single action (for simple tasks)
agent.click_element("Click the login button")
```

## How It Works

1. **Goal Analysis**: Takes a high-level goal and breaks it down into steps
2. **Screenshot Capture**: Takes a fresh screenshot of the current screen state
3. **AI Planning**: Uses Gemini to analyze the screen and determine:
   - Is the goal complete?
   - What is the next action needed?
   - Where should the action be performed?
4. **Action Execution**: Performs the action (click) using `pyautogui`
5. **Iteration**: Takes a new screenshot and repeats until the goal is achieved
6. **Adaptive**: Adapts to UI changes after each action by analyzing fresh screenshots

## Safety Features

- **Automatic Execution**: By default, clicks execute automatically after detection
- **Optional Confirmation**: Use `--confirm` flag to require confirmation before clicking
- **Failsafe**: PyAutoGUI's failsafe is enabled (move mouse to corner to abort)
- **Coordinate Display**: Shows detected coordinates before clicking

## Requirements

- Python 3.7+
- Google Generative AI API key
- macOS, Linux, or Windows

## Notes

- The agent uses normalized coordinates (0-1000) to work across different screen resolutions
- For simple UIs, use `gemini-1.5-flash` for faster responses
- For complex UIs with many elements, use `gemini-1.5-pro` for better accuracy
- **Note**: The `google-generativeai` package shows a deprecation warning but still works. Model names `gemini-1.5-flash` and `gemini-1.5-pro` are automatically mapped to `gemini-flash-latest` and `gemini-pro-latest` respectively
- On macOS, you'll need to grant Screen Recording permissions in System Settings > Privacy & Security > Screen Recording
