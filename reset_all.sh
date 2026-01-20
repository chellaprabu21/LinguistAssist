#!/bin/bash
# Reset all queues and restart services

set -e

echo "=== LinguistAssist Reset ==="
echo ""

# Stop all services
echo "1. Stopping services..."
launchctl stop com.jumpcloud.linguistassist 2>/dev/null || true
launchctl stop com.jumpcloud.linguistassist.api 2>/dev/null || true
pkill -f screenshot_service.py 2>/dev/null || true
pkill -f linguist_assist_service.py 2>/dev/null || true
sleep 2
echo "   ✓ Services stopped"

# Clear queues
echo ""
echo "2. Clearing queues..."
rm -rf ~/.linguist_assist/queue/* 2>/dev/null || true
rm -rf ~/.linguist_assist/processing/* 2>/dev/null || true
rm -rf ~/.linguist_assist/completed/* 2>/dev/null || true
echo "   ✓ Queue cleared"
echo "   ✓ Processing cleared"
echo "   ✓ Completed cleared"

# Restart services
echo ""
echo "3. Restarting services..."
launchctl start com.jumpcloud.linguistassist.api 2>/dev/null || true
sleep 2
launchctl start com.jumpcloud.linguistassist 2>/dev/null || true
sleep 3
echo "   ✓ Services restarted"

# Verify
echo ""
echo "4. Verifying services..."
API_HEALTH=$(curl -s http://localhost:8080/api/v1/health 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
SCREENSHOT_HEALTH=$(curl -s http://127.0.0.1:8081/health 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "unknown")

echo "   API Service: $API_HEALTH"
echo "   Screenshot Service: $SCREENSHOT_HEALTH"

# Queue status
QUEUE_COUNT=$(ls -1 ~/.linguist_assist/queue/ 2>/dev/null | wc -l | tr -d ' ')
PROCESSING_COUNT=$(ls -1 ~/.linguist_assist/processing/ 2>/dev/null | wc -l | tr -d ' ')
COMPLETED_COUNT=$(ls -1 ~/.linguist_assist/completed/ 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "=== Queue Status ==="
echo "   Queue: $QUEUE_COUNT tasks"
echo "   Processing: $PROCESSING_COUNT tasks"
echo "   Completed: $COMPLETED_COUNT tasks"
echo ""
echo "✓ Reset complete! Ready for new tasks."
