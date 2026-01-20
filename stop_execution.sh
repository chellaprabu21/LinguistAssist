#!/bin/bash
# Stop LinguistAssist task execution

set -e

echo "=== Stop LinguistAssist Execution ==="
echo ""
echo "Options:"
echo "1) Cancel a specific task (by ID)"
echo "2) Stop all services"
echo "3) Kill all processes (emergency)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        read -p "Enter task ID: " TASK_ID
        API_KEY=$(cat ~/.linguist_assist/api_config.json 2>/dev/null | grep -A 1 api_keys | grep -v api_keys | head -1 | tr -d ' ,"')
        if [ -z "$API_KEY" ]; then
            echo "Error: Could not find API key"
            exit 1
        fi
        
        echo "Cancelling task $TASK_ID..."
        curl -X DELETE -H "X-API-Key: $API_KEY" \
            "http://localhost:8080/api/v1/tasks/$TASK_ID" 2>/dev/null | python3 -m json.tool || echo "Task may already be processing or completed"
        ;;
    2)
        echo "Stopping all services..."
        launchctl stop com.jumpcloud.linguistassist 2>/dev/null || true
        launchctl stop com.jumpcloud.linguistassist.api 2>/dev/null || true
        pkill -f screenshot_service.py 2>/dev/null || true
        echo "✓ Services stopped"
        ;;
    3)
        echo "Killing all processes (emergency)..."
        pkill -9 -f linguist_assist_service.py 2>/dev/null || true
        pkill -9 -f screenshot_service.py 2>/dev/null || true
        pkill -9 -f linguist_assist_api.py 2>/dev/null || true
        echo "✓ All processes killed"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
