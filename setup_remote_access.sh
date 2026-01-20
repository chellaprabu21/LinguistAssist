#!/bin/bash
# Setup script for remote access to LinguistAssist API

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.jumpcloud.linguistassist.api.plist"
PLIST_FILE="$SCRIPT_DIR/$PLIST_NAME"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

echo "Setting up LinguistAssist API Server for remote access..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -q flask flask-cors || {
    echo "Error: Failed to install dependencies. Try: pip3 install flask flask-cors"
    exit 1
}

# Generate API key if config doesn't exist
CONFIG_FILE="$HOME/.linguist_assist/api_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Generating API key..."
    python3 "$SCRIPT_DIR/linguist_assist_api.py" --generate-key
fi

# Ask for configuration
echo ""
echo "API Server Configuration:"
read -p "Host to bind to [127.0.0.1] (use 0.0.0.0 for remote access): " HOST
HOST=${HOST:-127.0.0.1}

read -p "Port [8080]: " PORT
PORT=${PORT:-8080}

# Create plist file
cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.jumpcloud.linguistassist.api</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$SCRIPT_DIR/linguist_assist_api.py</string>
        <string>--host</string>
        <string>$HOST</string>
        <string>--port</string>
        <string>$PORT</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>$HOME/.linguist_assist/api.log</string>
    
    <key>StandardErrorPath</key>
    <string>$HOME/.linguist_assist/api_error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONPATH</key>
        <string>$SCRIPT_DIR</string>
    </dict>
    
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Copy plist file
echo "Installing Launch Agent..."
cp "$PLIST_FILE" "$INSTALLED_PLIST"

# Make scripts executable
chmod +x "$SCRIPT_DIR/linguist_assist_api.py"
chmod +x "$SCRIPT_DIR/api_client_example.py"

# Load the service
echo "Loading API service..."
launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true
launchctl load "$INSTALLED_PLIST"

echo ""
echo "✓ LinguistAssist API Server installed successfully!"
echo ""
echo "API Server:"
echo "  URL: http://$HOST:$PORT"
echo "  Health: http://$HOST:$PORT/api/v1/health"
echo ""
echo "Service commands:"
echo "  Start:   launchctl start com.jumpcloud.linguistassist.api"
echo "  Stop:    launchctl stop com.jumpcloud.linguistassist.api"
echo "  Status:  launchctl list | grep linguistassist.api"
echo "  Logs:    tail -f ~/.linguist_assist/api.log"
echo ""
echo "Get your API key:"
echo "  cat ~/.linguist_assist/api_config.json | grep -A 1 api_keys"
echo ""
echo "Test the API:"
echo "  python3 $SCRIPT_DIR/api_client_example.py --api-key YOUR_KEY --list"
echo ""
if [ "$HOST" = "127.0.0.1" ]; then
    echo "For remote access, use SSH tunnel:"
    echo "  ssh -L 8080:localhost:8080 user@your-mac-ip"
    echo ""
    echo "Or update the service to bind to 0.0.0.0 and restart."
fi
