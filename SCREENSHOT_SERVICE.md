# Screenshot Service Architecture

## Overview

The screenshot service solves the problem of Launch Agents not having GUI access on macOS. It runs as a separate process with GUI capabilities and provides screenshots to the main service via HTTP API.

## Architecture

```
┌─────────────────────┐
│  Launch Agent       │
│  (Main Service)     │
│  - No GUI access    │
│  - Handles tasks    │
└──────────┬──────────┘
           │
           │ HTTP Request
           │ (http://127.0.0.1:8081/screenshot)
           ▼
┌─────────────────────┐
│ Screenshot Service  │
│ - Runs silently     │
│ - Has GUI access    │
│ - Captures screens  │
└─────────────────────┘
           │
           │ pyautogui.screenshot()
           ▼
┌─────────────────────┐
│   macOS Screen       │
└─────────────────────┘
```

## How It Works

1. **Main Service Starts**: Launch Agent service starts and checks for screenshot service
2. **Auto-Launch**: If screenshot service is not running, main service launches it automatically
3. **Screenshot Requests**: When a task needs a screenshot, main service requests it via HTTP
4. **Screenshot Capture**: Screenshot service captures the screen using `pyautogui` (has GUI access)
5. **Response**: Screenshot is returned as base64-encoded PNG image
6. **Processing**: Main service decodes and uses the screenshot for AI analysis

## API Endpoints

### GET /health
Check if screenshot service is running.

**Response:**
```json
{
  "status": "healthy",
  "service": "screenshot"
}
```

### GET /screenshot or POST /screenshot
Capture and return a screenshot.

**Response:**
```json
{
  "success": true,
  "image": "base64-encoded-png-data",
  "width": 3024,
  "height": 1964,
  "format": "PNG"
}
```

## Usage

### Manual Start
```bash
python3 screenshot_service.py
```

### Silent/Daemon Mode
```bash
python3 screenshot_service.py --daemon
```

### Automatic Launch
The main service automatically launches the screenshot service when needed. No manual intervention required.

## Configuration

- **Port**: Default 8081 (configurable via `--port`)
- **Host**: 127.0.0.1 (localhost only, for security)
- **PID File**: `~/.linguist_assist/screenshot_service.pid`

## Benefits

1. **Solves GUI Access Issue**: Screenshot service runs with GUI access
2. **Automatic**: Launched automatically by main service
3. **Silent**: Runs in background, no visible windows
4. **Reliable**: Main service can verify screenshot service is running
5. **Fallback**: Main service falls back to direct methods if screenshot service unavailable

## Troubleshooting

### Screenshot service not starting
- Check if port 8081 is already in use
- Verify Python has screen recording permissions
- Check logs in `~/.linguist_assist/` directory

### Screenshots failing
- Ensure screenshot service is running: `curl http://127.0.0.1:8081/health`
- Check screen recording permissions in System Settings
- Verify Python.app has permissions

### Manual testing
```bash
# Start screenshot service
python3 screenshot_service.py --daemon

# Test health
curl http://127.0.0.1:8081/health

# Test screenshot
curl -X POST http://127.0.0.1:8081/screenshot | python3 -m json.tool
```
