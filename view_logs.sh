#!/bin/bash
# View LinguistAssist logs in real-time

LOG_DIR="$HOME/.linguist_assist"

echo "=== LinguistAssist Log Viewer ==="
echo ""
echo "Select log to view:"
echo "1) Main service log (service.log)"
echo "2) Service error log (service_error.log)"
echo "3) API server log (api.log)"
echo "4) API error log (api_error.log)"
echo "5) All logs (multitail)"
echo "6) Recent logs (last 50 lines)"
echo ""
read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo "Viewing service.log (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/service.log"
        ;;
    2)
        echo "Viewing service_error.log (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/service_error.log"
        ;;
    3)
        echo "Viewing api.log (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/api.log"
        ;;
    4)
        echo "Viewing api_error.log (Ctrl+C to exit)..."
        tail -f "$LOG_DIR/api_error.log"
        ;;
    5)
        echo "Viewing all logs (Ctrl+C to exit)..."
        # Use multitail if available, otherwise tail each file
        if command -v multitail &> /dev/null; then
            multitail "$LOG_DIR/service.log" "$LOG_DIR/service_error.log" "$LOG_DIR/api.log" "$LOG_DIR/api_error.log"
        else
            tail -f "$LOG_DIR/service.log" "$LOG_DIR/service_error.log" "$LOG_DIR/api.log" "$LOG_DIR/api_error.log"
        fi
        ;;
    6)
        echo "=== Recent Service Logs ==="
        tail -50 "$LOG_DIR/service.log" 2>/dev/null || echo "No service.log"
        echo ""
        echo "=== Recent Service Errors ==="
        tail -50 "$LOG_DIR/service_error.log" 2>/dev/null || echo "No service_error.log"
        echo ""
        echo "=== Recent API Logs ==="
        tail -50 "$LOG_DIR/api.log" 2>/dev/null || echo "No api.log"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
