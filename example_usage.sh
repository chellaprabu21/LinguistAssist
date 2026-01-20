#!/bin/bash
# Example usage script for LinguistAssist API

# Get API key from config
API_KEY=$(cat ~/.linguist_assist/api_config.json | grep -A 1 api_keys | grep -v api_keys | head -1 | tr -d ' ,"')
API_URL="http://localhost:8080/api/v1"

echo "=== LinguistAssist API Examples ==="
echo ""
echo "API Key: ${API_KEY:0:20}..."
echo "API URL: $API_URL"
echo ""

# Example 1: Health check
echo "1. Health Check (no auth required):"
echo "curl $API_URL/health"
echo ""
curl -s "$API_URL/health" | python3 -m json.tool
echo ""

# Example 2: Submit a simple task
echo "2. Submit Task: 'Click on the close button'"
echo "curl -X POST $API_URL/tasks \\"
echo "  -H \"X-API-Key: YOUR_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"goal\": \"Click on the close button\", \"max_steps\": 3}'"
echo ""

TASK_RESPONSE=$(curl -s -X POST "$API_URL/tasks" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Click on the close button", "max_steps": 3}')

echo "$TASK_RESPONSE" | python3 -m json.tool

TASK_ID=$(echo "$TASK_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])")

echo ""
echo "Task ID: $TASK_ID"
echo ""

# Wait a moment
sleep 2

# Example 3: Check task status
echo "3. Check Task Status:"
echo "curl -H \"X-API-Key: YOUR_KEY\" $API_URL/tasks/$TASK_ID"
echo ""

STATUS_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/tasks/$TASK_ID")
echo "$STATUS_RESPONSE" | python3 -m json.tool
echo ""

# Example 4: List all tasks
echo "4. List All Tasks:"
echo "curl -H \"X-API-Key: YOUR_KEY\" $API_URL/tasks"
echo ""

LIST_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/tasks?limit=5")
echo "$LIST_RESPONSE" | python3 -m json.tool
echo ""

echo "=== More Examples ==="
echo ""
echo "Submit a task to open an app:"
echo "curl -X POST $API_URL/tasks \\"
echo "  -H \"X-API-Key: $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"goal\": \"Open Finder application\", \"max_steps\": 5}'"
echo ""

echo "Submit a task to click a menu item:"
echo "curl -X POST $API_URL/tasks \\"
echo "  -H \"X-API-Key: $API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"goal\": \"Click on File menu and select New\", \"max_steps\": 5}'"
echo ""

echo "Wait for task to complete (using Python client):"
echo "python3 api_client_example.py --api-key $API_KEY --wait \"Your goal here\""
echo ""
