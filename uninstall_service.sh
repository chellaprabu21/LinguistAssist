#!/bin/bash
# Uninstall LinguistAssist service

set -e

PLIST_NAME="com.jumpcloud.linguistassist.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
INSTALLED_PLIST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

echo "Uninstalling LinguistAssist service..."

# Unload the service
if [ -f "$INSTALLED_PLIST" ]; then
    echo "Unloading service..."
    launchctl unload "$INSTALLED_PLIST" 2>/dev/null || true
    
    echo "Removing plist file..."
    rm "$INSTALLED_PLIST"
    
    echo "✓ Service uninstalled successfully!"
else
    echo "Service not found. Nothing to uninstall."
fi

echo ""
echo "Note: Log files and task queue are preserved in ~/.linguist_assist/"
echo "To remove them completely, run: rm -rf ~/.linguist_assist/"
