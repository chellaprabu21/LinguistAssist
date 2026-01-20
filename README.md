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

## Running as a Service (macOS)

LinguistAssist can run as a background service on macOS, allowing you to submit tasks without manually running the script each time.

### Installation

1. Install the service:
```bash
./install_service.sh
```

This will:
- Install LinguistAssist as a macOS Launch Agent
- Set up the service to start automatically on login
- Configure logging to `~/.linguist_assist/service.log`

### Service Management

```bash
# Start the service
launchctl start com.jumpcloud.linguistassist

# Stop the service
launchctl stop com.jumpcloud.linguistassist

# Check service status
launchctl list | grep linguistassist

# View service logs
tail -f ~/.linguist_assist/service.log
```

### Submitting Tasks

Once the service is running, submit tasks using the `submit_task.py` script:

```bash
# Submit a task
python3 submit_task.py "Log in to the website"

# Submit with custom max steps
python3 submit_task.py "Complete checkout process" --max-steps 30

# Check task status
python3 submit_task.py --status <task-id>
```

Tasks are queued in `~/.linguist_assist/queue/` and processed sequentially. Results are saved in `~/.linguist_assist/completed/`.

### Uninstallation

```bash
./uninstall_service.sh
```

**Note**: The service runs as a user agent (not a system daemon) to ensure it has access to the GUI and screen recording permissions.

## GUI Application

LinguistAssist includes a graphical user interface for easy task management.

### Running the GUI

```bash
python3 linguist_assist_gui.py
```

Or use the helper script:
```bash
./start_gui.sh
```

### GUI Features

- **Submit Tasks**: Enter goals and submit them with a click
- **Task Monitor**: View all tasks (queued, processing, completed, failed)
- **Task Details**: Click on any task to see detailed information
- **Auto-refresh**: Automatically updates task status every 5 seconds
- **Status Filtering**: Filter tasks by status (all, queued, processing, completed, failed)
- **API Settings**: Configure API URL and API key

The GUI communicates with the Launch Agent service via the HTTP API, so the service must be running for the GUI to work.

## Remote Access via HTTP API

LinguistAssist includes an HTTP API server that allows you to submit tasks remotely from any device or network.

### Setup

1. Install the API server:
```bash
./setup_remote_access.sh
```

This will:
- Install Flask dependencies
- Generate an API key (stored in `~/.linguist_assist/api_config.json`)
- Set up the API server as a Launch Agent
- Configure the server to run on startup

### API Endpoints

- `POST /api/v1/tasks` - Submit a new task
- `GET /api/v1/tasks/<id>` - Get task status
- `GET /api/v1/tasks` - List all tasks
- `DELETE /api/v1/tasks/<id>` - Cancel a queued task
- `GET /api/v1/health` - Health check (no auth required)

### Authentication

All endpoints (except `/health`) require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8080/api/v1/tasks \
  -d '{"goal": "Log in to the website", "max_steps": 20}'
```

Get your API key:
```bash
cat ~/.linguist_assist/api_config.json | grep -A 1 api_keys
```

### Remote Access Methods

#### Option 1: SSH Tunnel (Recommended)
```bash
# On remote machine
ssh -L 8080:localhost:8080 user@your-mac-ip

# Then access API at http://localhost:8080
curl -H "X-API-Key: your-key" http://localhost:8080/api/v1/tasks \
  -d '{"goal": "Click login button"}'
```

#### Option 2: Direct Network Access
Update the API server to bind to `0.0.0.0` instead of `127.0.0.1`:
```bash
# Edit ~/.linguist_assist/api_config.json and set "host": "0.0.0.0"
# Then restart: launchctl stop com.jumpcloud.linguistassist.api && launchctl start com.jumpcloud.linguistassist.api
```

Then access from remote machine:
```bash
curl -H "X-API-Key: your-key" http://your-mac-ip:8080/api/v1/tasks \
  -d '{"goal": "Click login button"}'
```

**Note**: Ensure your firewall allows incoming connections on port 8080.

#### Option 3: Cloud Proxy (ngrok)
```bash
# Install ngrok, then expose local API
ngrok http 8080

# Access via ngrok URL (includes HTTPS)
curl -H "X-API-Key: your-key" https://abc123.ngrok.io/api/v1/tasks \
  -d '{"goal": "Click login button"}'
```

### Python Client Example

```python
from api_client_example import LinguistAssistAPIClient

client = LinguistAssistAPIClient("http://localhost:8080", "your-api-key")

# Submit task
result = client.submit_task("Log in to the website", max_steps=20)
task_id = result["task_id"]

# Wait for completion
status = client.wait_for_task(task_id)
print(f"Task completed: {status['status']}")
```

### Command-Line Client

```bash
# Submit a task
python3 api_client_example.py --api-key YOUR_KEY "Log in to website"

# Submit and wait for completion
python3 api_client_example.py --api-key YOUR_KEY --wait "Log in to website"

# List all tasks
python3 api_client_example.py --api-key YOUR_KEY --list

# Check task status
python3 api_client_example.py --api-key YOUR_KEY --status <task-id>

# Cancel a task
python3 api_client_example.py --api-key YOUR_KEY --cancel <task-id>
```

### API Server Management

```bash
# Start API server
launchctl start com.jumpcloud.linguistassist.api

# Stop API server
launchctl stop com.jumpcloud.linguistassist.api

# Check status
launchctl list | grep linguistassist.api

# View logs
tail -f ~/.linguist_assist/api.log
```

### Security Features

- **API Key Authentication**: All requests require a valid API key
- **Rate Limiting**: Configurable requests per minute (default: 60)
- **IP Whitelisting**: Optional IP-based access control
- **Input Validation**: Validates task goals and parameters

See `REMOTE_ACCESS_PLAN.md` for detailed architecture and security considerations.

## Notes

- The agent uses normalized coordinates (0-1000) to work across different screen resolutions
- For simple UIs, use `gemini-1.5-flash` for faster responses
- For complex UIs with many elements, use `gemini-1.5-pro` for better accuracy
- **Note**: The `google-generativeai` package shows a deprecation warning but still works. Model names `gemini-1.5-flash` and `gemini-1.5-pro` are automatically mapped to `gemini-flash-latest` and `gemini-pro-latest` respectively
- On macOS, you'll need to grant Screen Recording permissions in System Settings > Privacy & Security > Screen Recording
- When running as a service, ensure the Terminal/Python process has Screen Recording permissions
