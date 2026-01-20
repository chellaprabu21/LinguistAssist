# How to Stop Task Execution

## Methods to Stop Execution

### 1. Cancel a Specific Task (Recommended)

If a task is queued (not yet processing), you can cancel it:

```bash
API_KEY="your-api-key"
TASK_ID="task-id-here"

curl -X DELETE -H "X-API-Key: $API_KEY" \
  http://localhost:8080/api/v1/tasks/$TASK_ID
```

**Note**: This only works for queued tasks. Tasks that are already processing cannot be cancelled via API (they will complete or fail).

### 2. Stop All Services

This stops the service from processing new tasks:

```bash
# Stop main service
launchctl stop com.jumpcloud.linguistassist

# Stop API server
launchctl stop com.jumpcloud.linguistassist.api

# Stop screenshot service
pkill -f screenshot_service.py
```

### 3. Emergency Kill (Force Stop)

If services are unresponsive:

```bash
# Kill all LinguistAssist processes
pkill -9 -f linguist_assist_service.py
pkill -9 -f screenshot_service.py
pkill -9 -f linguist_assist_api.py
```

### 4. Using the Helper Script

```bash
./stop_execution.sh
```

Interactive menu to:
- Cancel a specific task
- Stop all services
- Emergency kill all processes

## Current Task Status

Check what's running:

```bash
# List all tasks
API_KEY="your-api-key"
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8080/api/v1/tasks | python3 -m json.tool

# Check processing directory
ls -lh ~/.linguist_assist/processing/

# Check running processes
ps aux | grep linguist_assist | grep -v grep
```

## Stop Currently Processing Task

If a task is currently processing, you have limited options:

1. **Wait for it to complete** (it will finish or hit max_steps)
2. **Stop the service** (will stop processing but task may be left in processing/)
3. **Emergency kill** (force stop, may leave task in inconsistent state)

## Restart After Stopping

After stopping, restart services:

```bash
launchctl start com.jumpcloud.linguistassist.api
launchctl start com.jumpcloud.linguistassist
```

Or use the reset script:

```bash
./reset_all.sh
```

## Keyboard Interrupt (If Running Directly)

If you're running the service directly (not as Launch Agent), you can use:

- `Ctrl+C` - Graceful shutdown
- `Ctrl+Z` - Suspend (then `kill %1` to kill)

## PyAutoGUI Failsafe

PyAutoGUI has a built-in failsafe:
- **Move mouse to top-left corner** - This will raise an exception and stop execution
- However, this only works if the service is running in an interactive session

## Best Practices

1. **Monitor logs** while tasks run: `tail -f ~/.linguist_assist/service.log`
2. **Set reasonable max_steps** to prevent tasks from running too long
3. **Use task cancellation** for queued tasks before they start processing
4. **Stop services gracefully** when possible (not kill -9)

## Example: Stop Everything

```bash
# Stop services
launchctl stop com.jumpcloud.linguistassist
launchctl stop com.jumpcloud.linguistassist.api
pkill -f screenshot_service.py

# Verify stopped
ps aux | grep linguist_assist | grep -v grep

# Clear stuck tasks (if any)
rm -rf ~/.linguist_assist/processing/*

# Restart
launchctl start com.jumpcloud.linguistassist.api
launchctl start com.jumpcloud.linguistassist
```
