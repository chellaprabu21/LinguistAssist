#!/bin/bash
# Cancel all queued and processing tasks

set -e

API_KEY=$(cat ~/.linguist_assist/api_config.json 2>/dev/null | grep -A 1 api_keys | grep -v api_keys | head -1 | tr -d ' ,"')
API_URL="http://localhost:8080/api/v1"

if [ -z "$API_KEY" ]; then
    echo "Error: Could not find API key"
    exit 1
fi

echo "=== Cancelling All Tasks ==="
echo ""

# Get all tasks
TASKS_JSON=$(curl -s "$API_URL/tasks" -H "X-API-Key: $API_KEY")
QUEUED_TASKS=$(echo "$TASKS_JSON" | python3 -c "
import sys, json
tasks = json.load(sys.stdin).get('tasks', [])
queued = [t['id'] for t in tasks if t.get('status') in ['queued', 'processing']]
for task_id in queued:
    print(task_id)
" 2>/dev/null)

if [ -z "$QUEUED_TASKS" ]; then
    echo "No queued or processing tasks to cancel."
    exit 0
fi

# Count tasks
TASK_COUNT=$(echo "$QUEUED_TASKS" | wc -l | tr -d ' ')
echo "Found $TASK_COUNT task(s) to cancel"
echo ""

# Cancel each task
CANCELLED=0
FAILED=0

for TASK_ID in $QUEUED_TASKS; do
    echo -n "Cancelling $TASK_ID... "
    RESPONSE=$(curl -s -X DELETE "$API_URL/tasks/$TASK_ID" -H "X-API-Key: $API_KEY")
    
    if echo "$RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); exit(0 if d.get('status') == 'cancelled' else 1)" 2>/dev/null; then
        echo "✓"
        CANCELLED=$((CANCELLED + 1))
    else
        echo "✗"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "=== Summary ==="
echo "Cancelled: $CANCELLED"
echo "Failed: $FAILED"

# Also clear queue directories directly (for tasks that might not be in API)
echo ""
echo "Clearing queue directories..."
rm -f ~/.linguist_assist/queue/*.json 2>/dev/null || true
rm -f ~/.linguist_assist/processing/*.json 2>/dev/null || true
echo "✓ Queue directories cleared"

echo ""
echo "✓ All tasks cancelled!"
