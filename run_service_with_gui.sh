#!/bin/bash
# Run LinguistAssist service with GUI access
# This script ensures the service runs with proper GUI environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Export GUI-related environment variables
export DISPLAY=:0

# Run the service
exec /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
    "$SCRIPT_DIR/linguist_assist_service.py" \
    --model gemini-1.5-flash \
    --poll-interval 1.0
