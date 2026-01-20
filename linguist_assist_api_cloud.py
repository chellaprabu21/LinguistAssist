#!/usr/bin/env python3
"""
LinguistAssist HTTP API Server - Cloud-ready version with SQLite database.
Use this version for deploying to cloud platforms (Render, Railway, etc.)
"""

import json
import os
import sys
import time
import uuid
import secrets
import sqlite3
from pathlib import Path
from typing import Optional, Dict, List
from functools import wraps
from contextlib import contextmanager

from flask import Flask, request, jsonify
from flask_cors import CORS

# Database setup
DB_FILE = os.getenv('DATABASE_URL', 'sqlite:///linguist_assist.db').replace('sqlite:///', '')
if DB_FILE.startswith('/'):
    DB_PATH = DB_FILE
else:
    # For cloud platforms, use a persistent directory
    DB_PATH = os.path.join(os.getenv('HOME', '/tmp'), DB_FILE)

# Ensure directory exists
os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)

# API configuration
API_KEYS_ENV = os.getenv('API_KEYS', '')  # Comma-separated API keys
DEFAULT_RATE_LIMIT = int(os.getenv('RATE_LIMIT_RPM', '60'))

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Rate limiting storage (simple in-memory)
rate_limit_store = {}


def init_database():
    """Initialize SQLite database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                max_steps INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                timestamp REAL NOT NULL,
                source TEXT DEFAULT 'api',
                result TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON tasks(timestamp DESC)
        ''')
        
        conn.commit()


@contextmanager
def get_db():
    """Get database connection with proper cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_api_keys() -> List[str]:
    """Get API keys from environment variable or generate default."""
    if API_KEYS_ENV:
        return [key.strip() for key in API_KEYS_ENV.split(',') if key.strip()]
    
    # Generate a default key if none provided (for first run)
    default_key = secrets.token_urlsafe(32)
    print(f"⚠️  WARNING: No API_KEYS environment variable set!")
    print(f"Generated temporary API key: {default_key}")
    print(f"Set API_KEYS environment variable with your keys (comma-separated)")
    return [default_key]


def check_rate_limit(api_key: str) -> bool:
    """Check if API key has exceeded rate limit."""
    now = time.time()
    limit = DEFAULT_RATE_LIMIT
    
    if api_key not in rate_limit_store:
        rate_limit_store[api_key] = []
    
    # Clean old requests (older than 1 minute)
    rate_limit_store[api_key] = [
        ts for ts in rate_limit_store[api_key] 
        if now - ts < 60
    ]
    
    # Check limit
    if len(rate_limit_store[api_key]) >= limit:
        return False
    
    # Record this request
    rate_limit_store[api_key].append(now)
    return True


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({
                "error": "API key required",
                "message": "Provide API key via X-API-Key header or api_key query parameter"
            }), 401
        
        valid_keys = get_api_keys()
        if api_key not in valid_keys:
            return jsonify({
                "error": "Invalid API key"
            }), 401
        
        # Check rate limit
        if not check_rate_limit(api_key):
            return jsonify({
                "error": "Rate limit exceeded",
                "message": f"Maximum {DEFAULT_RATE_LIMIT} requests per minute"
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint (no auth required)."""
    try:
        # Test database connection
        with get_db() as conn:
            conn.execute('SELECT 1')
        
        return jsonify({
            "status": "healthy",
            "service": "LinguistAssist API",
            "version": "1.0.0-cloud",
            "database": "connected"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


@app.route('/api/v1/tasks', methods=['POST'])
@require_api_key
def submit_task():
    """Submit a new task to the queue."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Invalid request",
                "message": "JSON body required"
            }), 400
        
        goal = data.get('goal')
        if not goal:
            return jsonify({
                "error": "Invalid request",
                "message": "goal field is required"
            }), 400
        
        max_steps = data.get('max_steps', 20)
        task_id = data.get('id', str(uuid.uuid4()))
        
        # Validate max_steps
        try:
            max_steps = int(max_steps)
            if max_steps < 1 or max_steps > 100:
                return jsonify({
                    "error": "Invalid request",
                    "message": "max_steps must be between 1 and 100"
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "error": "Invalid request",
                "message": "max_steps must be a number"
            }), 400
        
        # Check if task ID already exists
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM tasks WHERE id = ?', (task_id,))
            if cursor.fetchone():
                return jsonify({
                    "error": "Task ID already exists",
                    "task_id": task_id
                }), 409
            
            # Insert task
            cursor.execute('''
                INSERT INTO tasks (id, goal, max_steps, status, timestamp, source)
                VALUES (?, ?, ?, 'queued', ?, 'api')
            ''', (task_id, goal, max_steps, time.time()))
        
        return jsonify({
            "task_id": task_id,
            "status": "queued",
            "message": "Task submitted successfully",
            "goal": goal,
            "max_steps": max_steps
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks/<task_id>', methods=['GET'])
@require_api_key
def get_task_status(task_id: str):
    """Get the status of a task."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, goal, max_steps, status, timestamp, source, result
                FROM tasks WHERE id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return jsonify({
                    "error": "Task not found",
                    "task_id": task_id
                }), 404
            
            task = dict(row)
            if task['result']:
                try:
                    task['result'] = json.loads(task['result'])
                except:
                    pass
            
            return jsonify(task), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks', methods=['GET'])
@require_api_key
def list_tasks():
    """List all tasks (queued, processing, completed)."""
    try:
        status_filter = request.args.get('status', 'all')
        limit = request.args.get('limit', type=int)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            if status_filter == 'all':
                cursor.execute('''
                    SELECT id, goal, max_steps, status, timestamp, source, result
                    FROM tasks
                    ORDER BY timestamp DESC
                ''')
            else:
                cursor.execute('''
                    SELECT id, goal, max_steps, status, timestamp, source, result
                    FROM tasks
                    WHERE status = ?
                    ORDER BY timestamp DESC
                ''', (status_filter,))
            
            rows = cursor.fetchall()
            tasks = []
            
            for row in rows:
                task = dict(row)
                if task['result']:
                    try:
                        task['result'] = json.loads(task['result'])
                    except:
                        pass
                tasks.append(task)
            
            if limit:
                tasks = tasks[:limit]
            
            return jsonify({
                "tasks": tasks,
                "count": len(tasks)
            }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks/<task_id>', methods=['DELETE'])
@require_api_key
def cancel_task(task_id: str):
    """Cancel a queued task."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check if task exists and is queued
            cursor.execute('SELECT status FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({
                    "error": "Task not found",
                    "task_id": task_id
                }), 404
            
            if row['status'] != 'queued':
                return jsonify({
                    "error": "Task cannot be cancelled",
                    "message": f"Task is already {row['status']}"
                }), 400
            
            # Update status to cancelled
            cursor.execute('''
                UPDATE tasks 
                SET status = 'cancelled', updated_at = strftime('%s', 'now')
                WHERE id = ?
            ''', (task_id,))
        
        return jsonify({
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancelled successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks/<task_id>/result', methods=['PUT'])
@require_api_key
def update_task_result(task_id: str):
    """Update task result (for worker service to call)."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        status = data.get('status', 'completed')
        result = json.dumps(data.get('result', {})) if data.get('result') else None
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tasks 
                SET status = ?, result = ?, updated_at = strftime('%s', 'now')
                WHERE id = ?
            ''', (status, result, task_id))
            
            if cursor.rowcount == 0:
                return jsonify({
                    "error": "Task not found",
                    "task_id": task_id
                }), 404
        
        return jsonify({
            "task_id": task_id,
            "status": status,
            "message": "Task result updated"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LinguistAssist HTTP API Server (Cloud Version)"
    )
    parser.add_argument(
        "--host",
        default=os.getenv('HOST', '0.0.0.0'),
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv('PORT', 8080)),
        help="Port to bind to (default: from PORT env var or 8080)"
    )
    
    args = parser.parse_args()
    
    # Initialize database
    print("Initializing database...")
    init_database()
    print(f"Database initialized: {DB_PATH}")
    
    # Check API keys
    api_keys = get_api_keys()
    if not api_keys or api_keys == ['']:
        print("⚠️  WARNING: No API keys configured!")
        print("Set API_KEYS environment variable: API_KEYS=key1,key2,key3")
    
    print(f"Starting LinguistAssist API server on {args.host}:{args.port}")
    print(f"Health check: http://{args.host}:{args.port}/api/v1/health")
    print(f"Database: {DB_PATH}")
    
    # Use gunicorn in production if available, otherwise Flask dev server
    if os.getenv('FLASK_ENV') == 'production' and 'gunicorn' in sys.modules:
        # Gunicorn will handle this
        pass
    else:
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
