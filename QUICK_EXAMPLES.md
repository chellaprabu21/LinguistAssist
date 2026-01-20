# Quick Examples for LinguistAssist API

## Prerequisites

Get your API key:
```bash
cat ~/.linguist_assist/api_config.json | grep -A 1 api_keys
```

Or use the script:
```bash
./example_usage.sh
```

## Example 1: Simple Task - Click a Button

```bash
API_KEY="your-api-key-here"

curl -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Click on the close button",
    "max_steps": 3
  }'
```

**Response:**
```json
{
  "task_id": "abc-123-def-456",
  "status": "queued",
  "message": "Task submitted successfully",
  "goal": "Click on the close button",
  "max_steps": 3
}
```

## Example 2: Check Task Status

```bash
TASK_ID="abc-123-def-456"

curl -H "X-API-Key: $API_KEY" \
  http://localhost:8080/api/v1/tasks/$TASK_ID
```

**Response:**
```json
{
  "id": "abc-123-def-456",
  "status": "completed",
  "goal": "Click on the close button",
  "max_steps": 3,
  "timestamp": 1768907669.6187499
}
```

## Example 3: Open an Application

```bash
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Open Finder application",
    "max_steps": 5
  }'
```

## Example 4: Click Menu Item

```bash
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Click on File menu and select New",
    "max_steps": 5
  }'
```

## Example 5: Type Text

```bash
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Click in the search bar and type hello",
    "max_steps": 8
  }'
```

## Example 6: List All Tasks

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8080/api/v1/tasks
```

## Example 7: List Tasks by Status

```bash
# Get only completed tasks
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/v1/tasks?status=completed"

# Get only queued tasks
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8080/api/v1/tasks?status=queued"
```

## Example 8: Using Python Client

```python
from api_client_example import LinguistAssistAPIClient

# Initialize client
client = LinguistAssistAPIClient(
    "http://localhost:8080",
    "your-api-key-here"
)

# Submit task
result = client.submit_task("Click on the close button", max_steps=3)
task_id = result["task_id"]
print(f"Task submitted: {task_id}")

# Wait for completion
status = client.wait_for_task(task_id)
print(f"Task completed: {status['status']}")
```

## Example 9: Command-Line Client

```bash
# Submit and wait
python3 api_client_example.py \
  --api-key YOUR_KEY \
  --wait \
  "Click on the close button"

# Just submit
python3 api_client_example.py \
  --api-key YOUR_KEY \
  "Open Finder"

# Check status
python3 api_client_example.py \
  --api-key YOUR_KEY \
  --status TASK_ID

# List all tasks
python3 api_client_example.py \
  --api-key YOUR_KEY \
  --list
```

## Example 10: Complete Workflow

```bash
#!/bin/bash
API_KEY="your-api-key"

# 1. Submit task
RESPONSE=$(curl -s -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Click on the close button", "max_steps": 3}')

TASK_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")
echo "Task submitted: $TASK_ID"

# 2. Wait and check status
for i in {1..10}; do
  STATUS=$(curl -s -H "X-API-Key: $API_KEY" \
    http://localhost:8080/api/v1/tasks/$TASK_ID)
  
  TASK_STATUS=$(echo $STATUS | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
  echo "Status: $TASK_STATUS"
  
  if [ "$TASK_STATUS" = "completed" ] || [ "$TASK_STATUS" = "failed" ]; then
    echo "Task finished!"
    break
  fi
  
  sleep 2
done
```

## Quick Test Script

Run the example script:
```bash
./example_usage.sh
```

This will:
1. Check API health
2. Submit a test task
3. Check task status
4. List all tasks
5. Show more examples

## Tips

- **Simple goals work best**: "Click the close button" is better than "Close all windows and clean up"
- **Use appropriate max_steps**: Simple tasks need 2-3 steps, complex ones need 10-20
- **Check status**: Tasks process asynchronously, check status to see results
- **Screen permissions**: Make sure Terminal/Python has screen recording permissions on macOS

## Common Goals

- `"Click on the close button"`
- `"Open Finder application"`
- `"Click on File menu"`
- `"Find and click the search icon"`
- `"Click in the address bar"`
- `"Type hello in the search box"`
- `"Press the Escape key"`
