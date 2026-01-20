#!/bin/bash
# Setup script to configure LinguistAssist to use Vercel cloud API

CLOUD_CONFIG_FILE="$HOME/.linguist_assist/cloud_config.json"
CONFIG_DIR="$HOME/.linguist_assist"

# Create config directory if it doesn't exist
mkdir -p "$CONFIG_DIR"

# Cloud API configuration
API_URL="https://linguist-assist.vercel.app"
API_KEY="mSawoFoDlUkNxi39RgpFJPUwxFOxdJ9TM3YAMsGKARs"

# Create cloud config file
cat > "$CLOUD_CONFIG_FILE" << EOF
{
  "api_url": "$API_URL",
  "api_key": "$API_KEY"
}
EOF

echo "✓ Cloud API configuration saved to: $CLOUD_CONFIG_FILE"
echo ""
echo "Configuration:"
echo "  API URL: $API_URL"
echo "  API Key: $API_KEY"
echo ""
echo "The GUI and API clients will now use the cloud API by default."
echo ""
echo "To switch back to local API, delete or rename:"
echo "  rm $CLOUD_CONFIG_FILE"
