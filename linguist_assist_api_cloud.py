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

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

# Database setup
# On Vercel and other serverless platforms, only /tmp is writable
DB_FILE = os.getenv('DATABASE_URL', 'sqlite:///linguist_assist.db').replace('sqlite:///', '')
if DB_FILE.startswith('/'):
    DB_PATH = DB_FILE
elif os.getenv('VERCEL') or os.getenv('VERCEL_ENV') or os.getenv('NOW_REGION'):
    # Vercel: use /tmp (only writable location)
    DB_PATH = os.path.join('/tmp', os.path.basename(DB_FILE))
else:
    # For other cloud platforms, try /tmp first (serverless-friendly)
    # Fall back to HOME if /tmp doesn't work
    DB_PATH = os.path.join('/tmp', os.path.basename(DB_FILE))

# Ensure directory exists (for /tmp, directory is always writable)
try:
    db_dir = os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.'
    if db_dir and db_dir != '.':
        os.makedirs(db_dir, exist_ok=True)
except Exception as e:
    # If directory creation fails, use /tmp directly
    print(f"Warning: Could not create database directory {db_dir}: {e}")
    DB_PATH = os.path.join('/tmp', os.path.basename(DB_FILE))

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
                device_id TEXT,
                result TEXT,
                created_at REAL DEFAULT (strftime('%s', 'now')),
                updated_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                last_seen REAL DEFAULT (strftime('%s', 'now')),
                status TEXT DEFAULT 'offline',
                created_at REAL DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        # Logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                timestamp REAL DEFAULT (strftime('%s', 'now')),
                level TEXT DEFAULT 'INFO',
                message TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON tasks(timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_device_id ON tasks(device_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_task_logs_task_id ON task_logs(task_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_task_logs_timestamp ON task_logs(timestamp DESC)
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


@app.route('/', methods=['GET'])
def index():
    """Serve the admin dashboard."""
    # Try multiple possible static directories (static, public, or current dir)
    possible_dirs = [
        os.path.join(os.path.dirname(__file__), 'static'),
        os.path.join(os.path.dirname(__file__), 'public'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public'),
        'static',
        'public',
    ]
    
    for static_dir in possible_dirs:
        html_path = os.path.join(static_dir, 'index.html')
        if os.path.exists(html_path):
            return send_from_directory(static_dir, 'index.html')
    
    # If HTML file not found, read it from the static directory in the repo
    # This handles Vercel deployment where files might be in different locations
    try:
        # Try to read the embedded HTML (we'll embed it as fallback)
        html_content = get_embedded_html()
        return html_content, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except:
        return jsonify({
            "message": "LinguistAssist API",
            "version": "1.0.0-cloud",
            "dashboard": "Dashboard HTML not found. Please ensure static/index.html exists.",
            "api_docs": "/api/v1/health"
        }), 200


def get_embedded_html():
    """Get embedded HTML for dashboard (fallback if file not found)."""
    # Read from static/index.html if it exists
    static_paths = [
        os.path.join(os.path.dirname(__file__), 'static', 'index.html'),
        os.path.join(os.path.dirname(__file__), 'public', 'index.html'),
        'static/index.html',
        'public/index.html',
    ]
    
    for path in static_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
    
    # Return minimal HTML that loads the dashboard
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LinguistAssist API</title>
        <style>body{font-family:sans-serif;padding:40px;text-align:center;}</style>
    </head>
    <body>
        <h1>LinguistAssist API</h1>
        <p>Dashboard HTML file not found. Please check deployment.</p>
        <p><a href="/api/v1/health">API Health Check</a></p>
    </body>
    </html>
    """


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
        device_id = data.get('device_id')
        
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
        
        # Validate device_id if provided
        if device_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM devices WHERE id = ?', (device_id,))
                if not cursor.fetchone():
                    return jsonify({
                        "error": "Invalid device ID",
                        "device_id": device_id
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
                INSERT INTO tasks (id, goal, max_steps, status, timestamp, source, device_id)
                VALUES (?, ?, ?, 'queued', ?, 'api', ?)
            ''', (task_id, goal, max_steps, time.time(), device_id))
        
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
                SELECT id, goal, max_steps, status, timestamp, source, device_id, result
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
                    SELECT id, goal, max_steps, status, timestamp, source, device_id, result
                    FROM tasks
                    ORDER BY timestamp DESC
                ''')
            else:
                cursor.execute('''
                    SELECT id, goal, max_steps, status, timestamp, source, device_id, result
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


@app.route('/api/v1/tasks/clear', methods=['DELETE'])
@require_api_key
def clear_tasks():
    """Clear all tasks (or filtered by status)."""
    try:
        status_filter = request.args.get('status', 'all')
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            if status_filter == 'all':
                cursor.execute('DELETE FROM tasks')
                cursor.execute('DELETE FROM task_logs')
            else:
                # Delete tasks with specific status and their logs
                cursor.execute('SELECT id FROM tasks WHERE status = ?', (status_filter,))
                task_ids = [row[0] for row in cursor.fetchall()]
                if task_ids:
                    placeholders = ','.join(['?'] * len(task_ids))
                    cursor.execute(f'DELETE FROM task_logs WHERE task_id IN ({placeholders})', task_ids)
                cursor.execute('DELETE FROM tasks WHERE status = ?', (status_filter,))
            
            deleted_count = cursor.rowcount
        
        return jsonify({
            "message": f"Cleared {deleted_count} tasks",
            "status_filter": status_filter,
            "deleted_count": deleted_count
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/devices', methods=['GET'])
@require_api_key
def list_devices():
    """List all registered devices."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, description, last_seen, status, created_at
                FROM devices
                ORDER BY last_seen DESC
            ''')
            
            devices = []
            for row in cursor.fetchall():
                devices.append(dict(row))
            
            return jsonify({
                "devices": devices,
                "count": len(devices)
            }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/devices', methods=['POST'])
@require_api_key
def register_device():
    """Register a new device."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Invalid request",
                "message": "JSON body required"
            }), 400
        
        device_id = data.get('id') or str(uuid.uuid4())
        name = data.get('name', f"Device {device_id[:8]}")
        description = data.get('description', '')
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check if device exists
            cursor.execute('SELECT id FROM devices WHERE id = ?', (device_id,))
            if cursor.fetchone():
                # Update existing device
                cursor.execute('''
                    UPDATE devices 
                    SET name = ?, description = ?, last_seen = strftime('%s', 'now'), status = 'online'
                    WHERE id = ?
                ''', (name, description, device_id))
            else:
                # Insert new device
                cursor.execute('''
                    INSERT INTO devices (id, name, description, last_seen, status)
                    VALUES (?, ?, ?, strftime('%s', 'now'), 'online')
                ''', (device_id, name, description))
        
        return jsonify({
            "device_id": device_id,
            "name": name,
            "message": "Device registered successfully"
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/devices/<device_id>/heartbeat', methods=['POST'])
@require_api_key
def device_heartbeat(device_id: str):
    """Update device heartbeat (called by devices to stay online)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE devices 
                SET last_seen = strftime('%s', 'now'), status = 'online'
                WHERE id = ?
            ''', (device_id,))
            
            if cursor.rowcount == 0:
                return jsonify({
                    "error": "Device not found",
                    "device_id": device_id
                }), 404
        
        return jsonify({
            "device_id": device_id,
            "status": "online",
            "message": "Heartbeat updated"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks/<task_id>/logs', methods=['GET'])
@require_api_key
def get_task_logs(task_id: str):
    """Get logs for a specific task."""
    try:
        limit = request.args.get('limit', type=int) or 1000
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, level, message
                FROM task_logs
                WHERE task_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (task_id, limit))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "timestamp": row[0],
                    "level": row[1],
                    "message": row[2]
                })
            
            # Reverse to show oldest first
            logs.reverse()
            
            return jsonify({
                "task_id": task_id,
                "logs": logs,
                "count": len(logs)
            }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks/<task_id>/logs', methods=['POST'])
@require_api_key
def add_task_log(task_id: str):
    """Add a log entry for a task (called by service)."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "Invalid request",
                "message": "JSON body required"
            }), 400
        
        level = data.get('level', 'INFO')
        message = data.get('message', '')
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_logs (task_id, level, message, timestamp)
                VALUES (?, ?, ?, strftime('%s', 'now'))
            ''', (task_id, level, message))
        
        return jsonify({
            "task_id": task_id,
            "message": "Log added successfully"
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks/claim', methods=['POST'])
@require_api_key
def claim_task():
    """Atomically claim a queued task for processing (prevents race conditions)."""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id')
        
        if not device_id:
            return jsonify({
                "error": "Invalid request",
                "message": "device_id is required"
            }), 400
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Find a queued task to claim
            cursor.execute('''
                SELECT id, goal, max_steps, status, timestamp, device_id
                FROM tasks 
                WHERE status = 'queued' 
                AND (device_id IS NULL OR device_id = ?)
                ORDER BY timestamp ASC 
                LIMIT 1
            ''', (device_id,))
            
            row = cursor.fetchone()
            
            if not row:
                # No tasks available
                return jsonify({
                    "message": "No tasks available",
                    "task": None
                }), 200
            
            task_id = row[0]
            
            # Atomically claim the task: set status to processing AND assign device_id
            # Only succeeds if task is still queued (prevents race conditions)
            cursor.execute('''
                UPDATE tasks 
                SET status = 'processing', device_id = ?, updated_at = strftime('%s', 'now')
                WHERE id = ? AND status = 'queued'
            ''', (device_id, task_id))
            
            if cursor.rowcount == 0:
                # Task was already claimed by another service
                return jsonify({
                    "message": "Task already claimed by another device",
                    "task": None
                }), 200
            
            # Fetch the updated task
            cursor.execute('''
                SELECT id, goal, max_steps, status, timestamp, device_id
                FROM tasks WHERE id = ?
            ''', (task_id,))
            
            row = cursor.fetchone()
            task = dict(row)
            return jsonify({
                "message": "Task claimed successfully",
                "task": task
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
