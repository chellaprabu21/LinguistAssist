"""
Vercel serverless function handler for LinguistAssist API
"""
import sys
import os

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from linguist_assist_api_cloud import app, init_database

# Initialize database on cold start (only once per instance)
# Note: On Vercel, the file system is ephemeral, so database resets on each deployment
# Use a flag to avoid re-initializing on every request
if not hasattr(app, '_db_initialized'):
    try:
        init_database()
        app._db_initialized = True
    except Exception as e:
        # If init fails, log but continue (might be already initialized)
        print(f"Database initialization note: {e}")

# Export the Flask app as 'handler' for Vercel's Python runtime
# Vercel expects the handler function to be named 'handler'
handler = app
