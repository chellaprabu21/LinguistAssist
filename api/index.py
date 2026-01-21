"""
Vercel serverless function handler for LinguistAssist API
"""
import sys
import os

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from linguist_assist_api_cloud import app, init_database
    
    # Initialize database on cold start (only once per instance)
    # Note: On Vercel, the file system is ephemeral, so database resets on each deployment
    # Use a flag to avoid re-initializing on every request
    if not hasattr(app, '_db_initialized'):
        try:
            init_database()
            app._db_initialized = True
            print("Database initialized successfully")
        except Exception as e:
            # If init fails, log but continue (might be already initialized)
            print(f"Database initialization warning: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            # Set flag anyway to avoid retrying on every request
            app._db_initialized = True
    
    # Export the Flask app as 'handler' for Vercel's Python runtime
    # Vercel expects the handler to be the Flask WSGI app directly
    handler = app
    
except Exception as e:
    # If import fails, create a minimal error handler
    from flask import Flask, jsonify
    error_app = Flask(__name__)
    
    @error_app.route('/', defaults={'path': ''})
    @error_app.route('/<path:path>')
    def error_handler(path):
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        print(f"Fatal error importing app: {error_msg}")
        print(f"Traceback: {traceback_str}")
        return jsonify({
            "error": "Internal server error",
            "message": f"Failed to initialize application: {error_msg}",
            "traceback": traceback_str
        }), 500
    
    handler = error_app
