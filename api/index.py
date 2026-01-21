"""
Vercel serverless function handler for LinguistAssist API
"""
import sys
import os

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from linguist_assist_api_cloud import app, init_database

# Initialize database on cold start
# Note: On Vercel, the file system is ephemeral, so database resets on each deployment
init_database()

# Export the Flask app for Vercel's Python runtime
# Vercel requires the handler to be exported
handler = app
