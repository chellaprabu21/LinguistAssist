#!/bin/bash
# Helper script to guide users through granting screen recording permissions

echo "=== LinguistAssist Permission Setup ==="
echo ""
echo "The service needs Screen Recording permissions to work."
echo ""
echo "Steps to grant permissions:"
echo ""
echo "1. Open System Settings (or System Preferences on older macOS)"
echo "2. Go to: Privacy & Security > Screen Recording"
echo "3. Enable the checkbox for:"
echo "   - Python.app (or Python 3.12)"
echo "   - Terminal (if you're running from terminal)"
echo ""
echo "4. Restart the service:"
echo "   launchctl stop com.jumpcloud.linguistassist"
echo "   launchctl start com.jumpcloud.linguistassist"
echo ""
echo "Or restart your Mac to ensure permissions take effect."
echo ""
echo "=== Checking current status ==="
echo ""

# Check if service is running
if ps aux | grep -q "[l]inguist_assist_service"; then
    echo "✓ Service is running"
else
    echo "✗ Service is not running"
    echo "  Start it with: launchctl start com.jumpcloud.linguistassist"
fi

echo ""
echo "=== Test after granting permissions ==="
echo "Submit a test task:"
echo ""
API_KEY=$(cat ~/.linguist_assist/api_config.json 2>/dev/null | grep -A 1 api_keys | grep -v api_keys | head -1 | tr -d ' ,"')
if [ -n "$API_KEY" ]; then
    echo "curl -X POST http://localhost:8080/api/v1/tasks \\"
    echo "  -H \"X-API-Key: $API_KEY\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"goal\": \"Click on the close button\", \"max_steps\": 3}'"
fi

echo ""
echo "=== Quick permission check ==="
echo "You can also open System Settings directly:"
echo "open 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'"
