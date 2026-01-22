#!/usr/bin/env python3
"""
LinguistAssist HTTP API Server - Enables remote task submission via REST API.
"""

import json
import os
import sys
import time
import uuid
import secrets
from pathlib import Path
from typing import Optional, Dict, List
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS

# Import shared queue utilities
LOG_DIR = Path.home() / ".linguist_assist"
LOG_DIR.mkdir(exist_ok=True)
QUEUE_DIR = LOG_DIR / "queue"
QUEUE_DIR.mkdir(exist_ok=True)
PROCESSING_DIR = LOG_DIR / "processing"
PROCESSING_DIR.mkdir(exist_ok=True)
COMPLETED_DIR = LOG_DIR / "completed"
COMPLETED_DIR.mkdir(exist_ok=True)

# API configuration
API_CONFIG_FILE = LOG_DIR / "api_config.json"
DEFAULT_CONFIG = {
    "host": "127.0.0.1",
    "port": 8080,
    "api_keys": [],
    "rate_limit": {
        "enabled": True,
        "requests_per_minute": 60
    },
    "allowed_ips": []
}

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)  # Enable CORS for cross-origin requests

# Rate limiting storage (simple in-memory)
rate_limit_store = {}


def load_config() -> Dict:
    """Load API configuration from file."""
    if API_CONFIG_FILE.exists():
        try:
            with open(API_CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                merged = DEFAULT_CONFIG.copy()
                merged.update(config)
                return merged
        except Exception as e:
            print(f"Error loading config: {e}, using defaults")
            return DEFAULT_CONFIG.copy()
    else:
        # Create default config with a generated API key
        api_key = secrets.token_urlsafe(32)
        config = DEFAULT_CONFIG.copy()
        config["api_keys"] = [api_key]
        save_config(config)
        print(f"Generated default API key: {api_key}")
        print(f"Save this key - it's stored in {API_CONFIG_FILE}")
        return config


def save_config(config: Dict):
    """Save API configuration to file."""
    try:
        with open(API_CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def check_rate_limit(api_key: str) -> bool:
    """Check if API key has exceeded rate limit."""
    config = load_config()
    if not config["rate_limit"]["enabled"]:
        return True
    
    now = time.time()
    limit = config["rate_limit"]["requests_per_minute"]
    
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
        
        config = load_config()
        if api_key not in config["api_keys"]:
            return jsonify({
                "error": "Invalid API key"
            }), 401
        
        # Check IP whitelist if configured
        if config["allowed_ips"]:
            client_ip = request.remote_addr
            if client_ip not in config["allowed_ips"]:
                return jsonify({
                    "error": "IP not allowed"
                }), 403
        
        # Check rate limit
        if not check_rate_limit(api_key):
            return jsonify({
                "error": "Rate limit exceeded",
                "message": f"Maximum {config['rate_limit']['requests_per_minute']} requests per minute"
            }), 429
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Serve the admin dashboard."""
    try:
        return app.send_static_file('index.html')
    except:
        return jsonify({
            "error": "Dashboard not found",
            "message": "Make sure index.html exists in the public directory"
        }), 404

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint (no auth required)."""
    return jsonify({
        "status": "healthy",
        "service": "LinguistAssist API",
        "version": "1.0.0"
    })


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
        
        # Create task file
        task = {
            "id": task_id,
            "goal": goal,
            "max_steps": max_steps,
            "timestamp": time.time(),
            "source": "api"
        }
        
        task_file = QUEUE_DIR / f"{task_id}.json"
        
        # Check if task ID already exists
        if task_file.exists():
            return jsonify({
                "error": "Task ID already exists",
                "task_id": task_id
            }), 409
        
        with open(task_file, 'w') as f:
            json.dump(task, f, indent=2)
        
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
        # Check completed
        result_file = COMPLETED_DIR / f"{task_id}_result.json"
        if result_file.exists():
            with open(result_file, 'r') as f:
                result = json.load(f)
            return jsonify(result), 200
        
        # Check processing
        result_file = PROCESSING_DIR / f"{task_id}_result.json"
        if result_file.exists():
            with open(result_file, 'r') as f:
                result = json.load(f)
            return jsonify(result), 200
        
        # Check queue
        queue_file = QUEUE_DIR / f"{task_id}.json"
        if queue_file.exists():
            with open(queue_file, 'r') as f:
                task = json.load(f)
            return jsonify({
                "id": task_id,
                "status": "queued",
                "goal": task.get("goal"),
                "max_steps": task.get("max_steps"),
                "timestamp": task.get("timestamp")
            }), 200
        
        return jsonify({
            "error": "Task not found",
            "task_id": task_id
        }), 404
        
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
        
        tasks = []
        
        # Get queued tasks
        if status_filter in ['all', 'queued']:
            for task_file in QUEUE_DIR.glob("*.json"):
                try:
                    with open(task_file, 'r') as f:
                        task = json.load(f)
                    tasks.append({
                        "id": task.get("id", task_file.stem),
                        "status": "queued",
                        "goal": task.get("goal"),
                        "max_steps": task.get("max_steps"),
                        "timestamp": task.get("timestamp")
                    })
                except Exception:
                    pass
        
        # Get processing tasks
        if status_filter in ['all', 'processing']:
            for result_file in PROCESSING_DIR.glob("*_result.json"):
                try:
                    with open(result_file, 'r') as f:
                        result = json.load(f)
                    tasks.append(result)
                except Exception:
                    pass
        
        # Get completed tasks
        if status_filter in ['all', 'completed', 'failed', 'error']:
            for result_file in COMPLETED_DIR.glob("*_result.json"):
                try:
                    with open(result_file, 'r') as f:
                        result = json.load(f)
                    if status_filter == 'all' or result.get('status') == status_filter:
                        tasks.append(result)
                except Exception:
                    pass
        
        # Sort by timestamp (newest first)
        tasks.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Limit results
        limit = request.args.get('limit', type=int)
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
        queue_file = QUEUE_DIR / f"{task_id}.json"
        
        if not queue_file.exists():
            return jsonify({
                "error": "Task not found or already processing",
                "task_id": task_id
            }), 404
        
        # Move to completed with cancelled status
        cancelled_file = COMPLETED_DIR / f"{task_id}_result.json"
        with open(cancelled_file, 'w') as f:
            json.dump({
                "id": task_id,
                "status": "cancelled",
                "timestamp": time.time()
            }, f, indent=2)
        
        queue_file.unlink()
        
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
    """Clear tasks by status."""
    try:
        status_filter = request.args.get('status', 'all')
        deleted_count = 0
        
        if status_filter == 'all':
            # Delete all tasks from all directories
            # Queue
            for task_file in QUEUE_DIR.glob("*.json"):
                task_file.unlink()
                deleted_count += 1
            
            # Processing
            for task_file in PROCESSING_DIR.glob("*.json"):
                task_file.unlink()
                deleted_count += 1
            
            # Completed/Failed
            for result_file in COMPLETED_DIR.glob("*_result.json"):
                result_file.unlink()
                deleted_count += 1
            for task_file in COMPLETED_DIR.glob("*.json"):
                if not task_file.name.endswith("_result.json"):
                    task_file.unlink()
                    deleted_count += 1
        else:
            # Delete by specific status
            if status_filter == 'queued':
                for task_file in QUEUE_DIR.glob("*.json"):
                    task_file.unlink()
                    deleted_count += 1
            elif status_filter == 'processing':
                for task_file in PROCESSING_DIR.glob("*.json"):
                    task_file.unlink()
                    deleted_count += 1
            elif status_filter in ['completed', 'failed', 'error']:
                for result_file in COMPLETED_DIR.glob("*_result.json"):
                    try:
                        with open(result_file, 'r') as f:
                            result = json.load(f)
                        if result.get('status') == status_filter:
                            result_file.unlink()
                            deleted_count += 1
                            # Also delete the task file if it exists
                            task_id = result.get('id', result_file.stem.replace('_result', ''))
                            task_file = COMPLETED_DIR / f"{task_id}.json"
                            if task_file.exists():
                                task_file.unlink()
                    except:
                        pass
        
        return jsonify({
            "deleted_count": deleted_count,
            "status": status_filter,
            "message": f"Cleared {deleted_count} tasks"
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/tasks/claim', methods=['POST'])
@require_api_key
def claim_task():
    """Atomically claim a queued task for processing (file-based version)."""
    try:
        data = request.get_json() or {}
        device_id = data.get('device_id')  # Optional, for compatibility
        
        # Find oldest queued task
        task_files = sorted(QUEUE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
        
        if not task_files:
            return jsonify({
                "message": "No tasks available",
                "task": None
            }), 200
        
        # Try to claim the first task by moving it to processing
        task_file = task_files[0]
        try:
            # Load task
            with open(task_file, 'r') as f:
                task = json.load(f)
            
            # Move to processing directory (atomic operation)
            processing_file = PROCESSING_DIR / task_file.name
            task_file.rename(processing_file)
            
            # Update task with processing status
            task['status'] = 'processing'
            if device_id:
                task['device_id'] = device_id
            
            # Save updated task to processing
            with open(processing_file, 'w') as f:
                json.dump(task, f, indent=2)
            
            return jsonify({
                "message": "Task claimed successfully",
                "task": {
                    "id": task.get("id", task_file.stem),
                    "goal": task.get("goal"),
                    "max_steps": task.get("max_steps", 20),
                    "status": "processing",
                    "timestamp": task.get("timestamp", time.time()),
                    "device_id": task.get("device_id")
                }
            }), 200
            
        except (OSError, json.JSONDecodeError) as e:
            # File was already claimed or corrupted
            return jsonify({
                "message": "Task already claimed by another device",
                "task": None
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
        result = data.get('result', {})
        
        # Check processing directory first
        processing_file = PROCESSING_DIR / f"{task_id}.json"
        result_file = PROCESSING_DIR / f"{task_id}_result.json"
        
        if not processing_file.exists():
            # Check if already completed
            completed_file = COMPLETED_DIR / f"{task_id}.json"
            if completed_file.exists():
                return jsonify({
                    "task_id": task_id,
                    "status": status,
                    "message": "Task already completed"
                }), 200
            else:
                return jsonify({
                    "error": "Task not found",
                    "task_id": task_id
                }), 404
        
        # Save result
        result_data = {
            "id": task_id,
            "status": status,
            "result": result,
            "timestamp": time.time()
        }
        
        with open(result_file, 'w') as f:
            json.dump(result_data, f, indent=2)
        
        # Move to completed if done
        if status in ['completed', 'failed', 'error']:
            completed_file = COMPLETED_DIR / f"{task_id}.json"
            processing_file.rename(completed_file)
            result_file.rename(COMPLETED_DIR / f"{task_id}_result.json")
        
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


# Task logs storage (in-memory for local API)
task_logs_store = {}

@app.route('/api/v1/tasks/<task_id>/logs', methods=['GET'])
@require_api_key
def get_task_logs(task_id: str):
    """Get logs for a specific task."""
    try:
        limit = request.args.get('limit', type=int) or 2000
        
        logs = task_logs_store.get(task_id, [])
        
        # Sort by timestamp (oldest first)
        logs.sort(key=lambda x: x.get('timestamp', 0))
        
        # Limit results
        logs = logs[-limit:] if limit else logs
        
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
        
        if task_id not in task_logs_store:
            task_logs_store[task_id] = []
        
        log_entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message
        }
        
        task_logs_store[task_id].append(log_entry)
        
        # Keep only last 5000 logs per task
        if len(task_logs_store[task_id]) > 5000:
            task_logs_store[task_id] = task_logs_store[task_id][-5000:]
        
        return jsonify({
            "task_id": task_id,
            "message": "Log added successfully"
        }), 201
        
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


# Device endpoints (simplified, for compatibility)
@app.route('/api/v1/devices', methods=['POST'])
@require_api_key
def register_device():
    """Register a device (simplified for local mode)."""
    try:
        data = request.get_json() or {}
        device_id = data.get('id', 'local-device')
        
        return jsonify({
            "device_id": device_id,
            "message": "Device registered successfully"
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500


@app.route('/api/v1/devices/<device_id>/heartbeat', methods=['POST'])
@require_api_key
def device_heartbeat(device_id: str):
    """Update device heartbeat (simplified for local mode)."""
    return jsonify({
        "device_id": device_id,
        "message": "Heartbeat received"
    }), 200


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LinguistAssist HTTP API Server"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Host to bind to (default: from config or 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port to bind to (default: from config or 8080)"
    )
    parser.add_argument(
        "--generate-key",
        action="store_true",
        help="Generate a new API key and exit"
    )
    
    args = parser.parse_args()
    
    # Generate API key if requested
    if args.generate_key:
        api_key = secrets.token_urlsafe(32)
        config = load_config()
        if api_key not in config["api_keys"]:
            config["api_keys"].append(api_key)
            save_config(config)
        print(f"Generated API key: {api_key}")
        print(f"Use this key in X-API-Key header: X-API-Key: {api_key}")
        return 0
    
    # Load config
    config = load_config()
    
    host = args.host or config.get("host", "127.0.0.1")
    port = args.port or config.get("port", 8080)
    
    print(f"Starting LinguistAssist API server on {host}:{port}")
    print(f"API config: {API_CONFIG_FILE}")
    print(f"Health check: http://{host}:{port}/api/v1/health")
    
    if not config["api_keys"]:
        print("WARNING: No API keys configured! Generating one...")
        api_key = secrets.token_urlsafe(32)
        config["api_keys"] = [api_key]
        save_config(config)
        print(f"Generated API key: {api_key}")
    
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
