#!/bin/bash
# Install LinguistAssist as a macOS Launch Agent service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.jumpcloud.linguistassist.plist"
PLIST_FILE="$SCRIPT_DIR/$PLIST_NAME"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

echo "Installing LinguistAssist service..."

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Check if the plist file exists
if [ ! -f "$PLIST_FILE" ]; then
    echo "Error: $PLIST_FILE not found"
    exit 1
fi

# Update the plist file with the actual script path
echo "Updating plist file with correct paths..."
sed -i.bak "s|/Users/cv/Repo/LinguistAssist|$SCRIPT_DIR|g" "$PLIST_FILE"
sed -i.bak "s|/Users/cv|$HOME|g" "$PLIST_FILE"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"

# Copy plist file
echo "Copying plist file to $LAUNCH_AGENTS_DIR..."
cp "$PLIST_FILE" "$INSTALLED_PLIST"

# Make scripts executable
chmod +x "$SCRIPT_DIR/linguist_assist_service.py"
chmod +x "$SCRIPT_DIR/submit_task.py"

# Load the service
echo "Loading service..."
launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true
launchctl load "$INSTALLED_PLIST"

echo ""
echo "✓ LinguistAssist service installed successfully!"
echo ""
echo "Service commands:"
echo "  Start:   launchctl start com.jumpcloud.linguistassist"
echo "  Stop:    launchctl stop com.jumpcloud.linguistassist"
echo "  Status:  launchctl list | grep linguistassist"
echo "  Logs:    tail -f ~/.linguist_assist/service.log"
echo ""
echo "Submit a task:"
echo "  python3 $SCRIPT_DIR/submit_task.py 'Your goal here'"
echo ""
