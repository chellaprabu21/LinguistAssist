#!/bin/bash
# Check LinguistAssist service status and diagnose issues

echo "=== LinguistAssist Service Status ==="
echo ""

# Check if service is running
echo "1. Service Status:"
if launchctl list | grep -q "com.jumpcloud.linguistassist"; then
    echo "   ✓ Main service is loaded"
    launchctl list | grep "com.jumpcloud.linguistassist" | head -1
else
    echo "   ✗ Main service is NOT running"
fi

echo ""

# Check logs for errors
echo "2. Recent Log Entries:"
if [ -f ~/.linguist_assist/service.log ]; then
    echo "   Last 20 lines of service.log:"
    tail -20 ~/.linguist_assist/service.log | sed 's/^/   /'
else
    echo "   ✗ No service.log file found"
fi

echo ""

# Check error logs
echo "3. Error Log Entries:"
if [ -f ~/.linguist_assist/service_error.log ]; then
    echo "   Last 10 lines of service_error.log:"
    tail -10 ~/.linguist_assist/service_error.log | sed 's/^/   /'
else
    echo "   ✓ No errors in error log"
fi

echo ""

# Check API key configuration
echo "4. API Key Configuration:"
if [ -f ~/.linguist_assist/gemini_api_key.txt ]; then
    API_KEY=$(cat ~/.linguist_assist/gemini_api_key.txt)
    if [ -n "$API_KEY" ]; then
        echo "   ✓ Gemini API key found: ${API_KEY:0:20}..."
    else
        echo "   ✗ Gemini API key file is empty"
    fi
else
    echo "   ✗ Gemini API key file not found: ~/.linguist_assist/gemini_api_key.txt"
fi

echo ""

# Check cloud config
echo "5. Cloud API Configuration:"
if [ -f ~/.linguist_assist/cloud_config.json ]; then
    echo "   ✓ Cloud config found:"
    cat ~/.linguist_assist/cloud_config.json | python3 -m json.tool 2>/dev/null | sed 's/^/   /' || cat ~/.linguist_assist/cloud_config.json | sed 's/^/   /'
else
    echo "   ✗ Cloud config not found"
fi

echo ""

# Check device registration
echo "6. Device Registration:"
if [ -f ~/.linguist_assist/device_id.txt ]; then
    DEVICE_ID=$(cat ~/.linguist_assist/device_id.txt)
    echo "   ✓ Device ID: $DEVICE_ID"
else
    echo "   ✗ Device ID not found (service may not be registered)"
fi

echo ""

# Check if agent can initialize
echo "7. Testing Agent Initialization:"
cd /Applications/LinguistAssist 2>/dev/null || cd "$(dirname "$0")"
if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from linguist_assist import LinguistAssist
    agent = LinguistAssist()
    print('   ✓ Agent initialized successfully')
except Exception as e:
    print(f'   ✗ Agent initialization failed: {e}')
    sys.exit(1)
" 2>&1 | sed 's/^/   /'; then
    echo "   ✓ Agent can be initialized"
else
    echo "   ✗ Agent initialization failed - check API key"
fi

echo ""
echo "=== End of Status Check ==="
