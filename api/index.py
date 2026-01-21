"""
Vercel serverless function handler for LinguistAssist API
"""
import sys
import os

# Add parent directory to path to import the Flask app
parent_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, parent_dir)

# Set Vercel environment variable for database path detection
os.environ['VERCEL'] = '1'

# Try to import and initialize
try:
    from linguist_assist_api_cloud import app, init_database
    
    # Initialize database on import (Vercel serverless functions)
    # Use a flag to avoid re-initializing on every request
    if not hasattr(app, '_db_initialized'):
        try:
            init_database()
            app._db_initialized = True
            print("Database initialized successfully")
        except Exception as e:
            # Don't fail - log error and try to initialize on first request
            print(f"Database initialization deferred: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            app._db_initialized = False
    
    # Export the Flask app as 'handler' for Vercel's Python runtime
    handler = app
    
except Exception as e:
    # If import fails, create minimal Flask app with error info
    from flask import Flask, jsonify
    import traceback
    
    error_app = Flask(__name__)
    error_msg = str(e)
    error_traceback = traceback.format_exc()
    
    print(f"CRITICAL: Failed to import app: {error_msg}")
    print(f"Traceback: {error_traceback}")
    
    @error_app.route('/', defaults={'path': ''})
    @error_app.route('/<path:path>')
    def error_handler(path):
        return jsonify({
            "error": "Initialization failed",
            "message": error_msg,
            "traceback": error_traceback,
            "path": path
        }), 500
    
    handler = error_app
