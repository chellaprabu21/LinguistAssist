# Viewing LinguistAssist Logs

## Quick Commands

### Main Service Log (Most Important)
```bash
tail -f ~/.linguist_assist/service.log
```
This shows:
- Task processing
- Screenshot captures
- Action execution
- Task completion status

### Service Error Log
```bash
tail -f ~/.linguist_assist/service_error.log
```
Shows errors and exceptions from the main service.

### API Server Log
```bash
tail -f ~/.linguist_assist/api.log
```
Shows API requests and responses.

### API Error Log
```bash
tail -f ~/.linguist_assist/api_error.log
```
Shows API server errors.

### View All Logs at Once
```bash
tail -f ~/.linguist_assist/*.log
```

## Using the Helper Script

```bash
./view_logs.sh
```

This interactive script lets you choose which log to view.

## Filtering Logs

### Filter for specific task
```bash
tail -f ~/.linguist_assist/service.log | grep "TASK_ID"
```

### Filter for errors only
```bash
tail -f ~/.linguist_assist/service.log | grep -i error
```

### Filter for clicks
```bash
tail -f ~/.linguist_assist/service.log | grep -i "clicking\|click executed"
```

### Filter for screenshots
```bash
tail -f ~/.linguist_assist/service.log | grep -i screenshot
```

## View Recent Logs (Last N Lines)

```bash
# Last 50 lines
tail -50 ~/.linguist_assist/service.log

# Last 100 lines
tail -100 ~/.linguist_assist/service.log

# Last 20 lines with context
tail -20 ~/.linguist_assist/service.log
```

## Search Logs

```bash
# Search for a specific task
grep "TASK_ID" ~/.linguist_assist/service.log

# Search for errors
grep -i error ~/.linguist_assist/service.log

# Search with context (5 lines before/after)
grep -C 5 "error" ~/.linguist_assist/service.log
```

## Log File Locations

All logs are stored in: `~/.linguist_assist/`

- `service.log` - Main service output
- `service_error.log` - Service errors
- `api.log` - API server output
- `api_error.log` - API server errors

## Example: Monitor Task Execution

```bash
# Terminal 1: Submit a task and get task ID
TASK_ID="your-task-id"

# Terminal 2: Watch logs filtered for that task
tail -f ~/.linguist_assist/service.log | grep "$TASK_ID"
```

## Example: Watch Everything

```bash
# Open multiple terminal windows:
# Terminal 1:
tail -f ~/.linguist_assist/service.log

# Terminal 2:
tail -f ~/.linguist_assist/service_error.log

# Terminal 3:
tail -f ~/.linguist_assist/api.log
```
