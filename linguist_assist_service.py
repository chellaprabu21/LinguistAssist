#!/usr/bin/env python3
"""
LinguistAssist Service - Runs as a background daemon to accept and execute tasks.
"""

import json
import os
import sys
import time
import signal
import logging
import subprocess
import requests
from pathlib import Path
from typing import Optional, Dict

from linguist_assist import LinguistAssist

# Configure logging
LOG_DIR = Path.home() / ".linguist_assist"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "service.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Task queue directory (for fallback/local mode)
QUEUE_DIR = LOG_DIR / "queue"
QUEUE_DIR.mkdir(exist_ok=True)
PROCESSING_DIR = LOG_DIR / "processing"
PROCESSING_DIR.mkdir(exist_ok=True)
COMPLETED_DIR = LOG_DIR / "completed"
COMPLETED_DIR.mkdir(exist_ok=True)

# Cloud API configuration
CLOUD_CONFIG_FILE = LOG_DIR / "cloud_config.json"
DEFAULT_API_URL = "http://localhost:8080"
CLOUD_API_URL = "https://linguist-assist.vercel.app"

# Service control
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    running = False


class LinguistAssistService:
    """Service daemon for LinguistAssist."""
    
    def __init__(self, model_name: str = "gemini-1.5-flash", poll_interval: float = 5.0):
        """
        Initialize the service.
        
        Args:
            model_name: Gemini model to use
            poll_interval: How often to check for new tasks (seconds)
        """
        self.model_name = model_name
        self.poll_interval = poll_interval
        self.agent = None
        self.api_url, self.api_key = self.load_cloud_config()
        self.device_id = None
        logger.info(f"Initializing LinguistAssist service with model: {model_name}")
        logger.info(f"Cloud API URL: {self.api_url}")
    
    def load_cloud_config(self):
        """Load cloud API configuration."""
        # Try cloud config first
        try:
            if CLOUD_CONFIG_FILE.exists():
                with open(CLOUD_CONFIG_FILE, 'r') as f:
                    cloud_config = json.load(f)
                    api_url = cloud_config.get("api_url", CLOUD_API_URL)
                    api_key = cloud_config.get("api_key")
                    if api_key:
                        return api_url, api_key
        except Exception as e:
            logger.warning(f"Error loading cloud config: {e}")
        
        # Fall back to local config
        try:
            api_config_file = LOG_DIR / "api_config.json"
            if api_config_file.exists():
                with open(api_config_file, 'r') as f:
                    config = json.load(f)
                    api_keys = config.get("api_keys", [])
                    if api_keys:
                        return DEFAULT_API_URL, api_keys[0]
        except Exception as e:
            logger.warning(f"Error loading local config: {e}")
        
        logger.error("No API configuration found! Service will not be able to fetch tasks.")
        return None, None
        
    def ensure_screenshot_service(self):
        """Ensure screenshot service is running."""
        try:
            # Check if screenshot service is running
            response = requests.get("http://127.0.0.1:8081/health", timeout=1)
            if response.status_code == 200:
                logger.info("Screenshot service is running")
                return True
        except Exception:
            pass
        
        # Start screenshot service
        try:
            script_dir = Path(__file__).parent
            screenshot_script = script_dir / "screenshot_service.py"
            
            logger.info("Starting screenshot service...")
            # Use 'open' command to launch in GUI context (macOS)
            # This ensures the process runs with GUI access
            try:
                subprocess.Popen(
                    ['open', '-a', 'Python', '--args', str(screenshot_script), '--daemon'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            except Exception:
                # Fallback to direct launch if 'open' fails
                subprocess.Popen(
                    [sys.executable, str(screenshot_script), "--daemon"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    env=dict(os.environ, **{'DISPLAY': ':0'})  # Try to set display
                )
            
            # Wait a moment for it to start
            time.sleep(2)
            
            # Verify it's running
            response = requests.get("http://127.0.0.1:8081/health", timeout=2)
            if response.status_code == 200:
                logger.info("Screenshot service started successfully")
                return True
            else:
                logger.warning("Screenshot service may not have started properly")
                return False
        except Exception as e:
            logger.warning(f"Could not start screenshot service: {e}")
            return False
    
    def initialize_agent(self):
        """Initialize the LinguistAssist agent."""
        try:
            # Ensure screenshot service is running
            self.ensure_screenshot_service()
            
            self.agent = LinguistAssist(model_name=self.model_name)
            logger.info("LinguistAssist agent initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            return False
    
    def fetch_queued_tasks(self) -> list:
        """Fetch queued tasks from cloud API (for this device or unassigned)."""
        if not self.api_url or not self.api_key:
            return []
        
        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            # Fetch tasks that are queued and either unassigned or assigned to this device
            response = requests.get(
                f"{self.api_url}/api/v1/tasks?status=queued",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            tasks = data.get("tasks", [])
            
            # Filter: only process tasks assigned to this device or unassigned (device_id is None)
            if self.device_id:
                tasks = [t for t in tasks if t.get("device_id") is None or t.get("device_id") == self.device_id]
            else:
                # If device not registered, only take unassigned tasks
                tasks = [t for t in tasks if t.get("device_id") is None]
            
            return tasks
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch tasks from API: {e}")
            return []
    
    def send_log(self, task_id: str, level: str, message: str):
        """Send log entry to cloud API."""
        if not self.api_url or not self.api_key:
            return False
        
        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            requests.post(
                f"{self.api_url}/api/v1/tasks/{task_id}/logs",
                json={"level": level, "message": message},
                headers=headers,
                timeout=5
            )
            return True
        except:
            return False
    
    def register_device(self):
        """Register this service as a device."""
        if not self.api_url or not self.api_key:
            return None
        
        try:
            import socket
            import platform
            
            device_id = f"{socket.gethostname()}-{platform.system()}"
            device_name = f"{socket.gethostname()} ({platform.system()})"
            
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            response = requests.post(
                f"{self.api_url}/api/v1/devices",
                json={"id": device_id, "name": device_name, "description": "LinguistAssist Service"},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            self.device_id = device_id
            logger.info(f"Registered as device: {device_id}")
            return device_id
        except Exception as e:
            logger.warning(f"Failed to register device: {e}")
            return None
    
    def send_heartbeat(self):
        """Send heartbeat to keep device status online."""
        if not self.api_url or not self.api_key or not hasattr(self, 'device_id'):
            return
        
        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            requests.post(
                f"{self.api_url}/api/v1/devices/{self.device_id}/heartbeat",
                headers=headers,
                timeout=5
            )
        except:
            pass
    
    def update_task_status(self, task_id: str, status: str, result: Optional[Dict] = None):
        """Update task status in cloud API."""
        if not self.api_url or not self.api_key:
            logger.warning(f"Cannot update task {task_id} status - no API configuration")
            return False
        
        try:
            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json"
            }
            data = {
                "status": status
            }
            if result:
                data["result"] = result
            
            response = requests.put(
                f"{self.api_url}/api/v1/tasks/{task_id}/result",
                json=data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update task {task_id} status: {e}")
            return False
    
    def load_task(self, task_file: Path) -> Optional[Dict]:
        """Load a task from a JSON file (for local fallback)."""
        try:
            with open(task_file, 'r') as f:
                task = json.load(f)
            return task
        except Exception as e:
            logger.error(f"Failed to load task from {task_file}: {e}")
            return None
    
    def save_task_result(self, task_file: Path, result: Dict, status: str = "completed"):
        """Save task result to appropriate directory."""
        try:
            if status == "completed":
                target_dir = COMPLETED_DIR
            else:
                target_dir = PROCESSING_DIR
            
            result_file = target_dir / f"{task_file.stem}_result.json"
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            # Move task file to completed/processing
            task_file.rename(target_dir / task_file.name)
            logger.info(f"Task result saved to {result_file}")
        except Exception as e:
            logger.error(f"Failed to save task result: {e}")
    
    def process_task(self, task: Dict) -> bool:
        """
        Process a single task from cloud API.
        
        Args:
            task: Task dictionary from API
        
        Returns:
            True if task was processed successfully, False otherwise
        """
        task_id = task.get("id", "unknown")
        goal = task.get("goal", "")
        max_steps = task.get("max_steps", 20)
        
        logger.info(f"Processing task: {task_id} - {goal}")
        
        if not goal:
            logger.error(f"Task {task_id} has no goal specified")
            self.update_task_status(task_id, "error", {"error": "No goal specified"})
            return False
        
        # Update status to processing
        self.update_task_status(task_id, "processing")
        
        # Execute task with logging
        try:
            logger.info(f"Executing goal: {goal} (max_steps: {max_steps})")
            self.send_log(task_id, "INFO", f"Starting task execution: {goal}")
            
            # Create a custom logger that sends to API
            import logging
            class APILogHandler(logging.Handler):
                def __init__(self, service, task_id):
                    super().__init__()
                    self.service = service
                    self.task_id = task_id
                
                def emit(self, record):
                    try:
                        level = record.levelname
                        message = self.format(record)
                        self.service.send_log(self.task_id, level, message)
                    except:
                        pass
            
            # Add API log handler temporarily
            api_handler = APILogHandler(self, task_id)
            api_handler.setLevel(logging.INFO)
            logger.addHandler(api_handler)
            
            try:
                success = self.agent.execute_task(goal, max_steps=max_steps)
            finally:
                logger.removeHandler(api_handler)
            
            result = {
                "id": task_id,
                "goal": goal,
                "status": "completed" if success else "failed",
                "max_steps": max_steps,
                "success": success,
                "timestamp": time.time()
            }
            
            # Update task status in cloud API
            self.update_task_status(task_id, "completed" if success else "failed", result)
            logger.info(f"Task {task_id} completed: {success}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            result = {
                "id": task_id,
                "goal": goal,
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
            self.update_task_status(task_id, "error", result)
            return False
    
    def run(self):
        """Main service loop."""
        global running
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Initialize agent
        if not self.initialize_agent():
            logger.error("Failed to initialize agent, exiting")
            return 1
        
        # Register as device
        if self.api_url and self.api_key:
            self.register_device()
        
        logger.info("LinguistAssist service started")
        if self.api_url:
            logger.info(f"Polling cloud API: {self.api_url}")
            if self.device_id:
                logger.info(f"Registered as device: {self.device_id}")
        else:
            logger.warning("No API configuration - falling back to local file queue")
            logger.info(f"Monitoring local task queue: {QUEUE_DIR}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        # Send heartbeat every 30 seconds
        last_heartbeat = time.time()
        
        # Main loop
        while running:
            try:
                # Send heartbeat periodically
                if self.api_url and self.api_key and hasattr(self, 'device_id') and self.device_id:
                    if time.time() - last_heartbeat > 30:
                        self.send_heartbeat()
                        last_heartbeat = time.time()
                
                if self.api_url and self.api_key:
                    # Poll cloud API for queued tasks
                    tasks = self.fetch_queued_tasks()
                    
                    if tasks:
                        # Process tasks one at a time
                        task = tasks[0]
                        self.process_task(task)
                    else:
                        # No tasks, sleep
                        time.sleep(self.poll_interval)
                else:
                    # Fallback to local file queue
                    task_files = list(QUEUE_DIR.glob("*.json"))
                    
                    if task_files:
                        # Process tasks one at a time
                        task_file = task_files[0]
                        task = self.load_task(task_file)
                        if task:
                            self.process_task(task)
                            # Remove processed file
                            try:
                                task_file.unlink()
                            except:
                                pass
                    else:
                        # No tasks, sleep
                        time.sleep(self.poll_interval)
                    
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                running = False
                break
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
                time.sleep(self.poll_interval)
        
        logger.info("LinguistAssist service stopped")
        return 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LinguistAssist Service - Background daemon for GUI automation"
    )
    parser.add_argument(
        "--model",
        choices=["gemini-1.5-flash", "gemini-1.5-pro"],
        default="gemini-1.5-flash",
        help="Gemini model to use (default: gemini-1.5-flash)"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=5.0,
        help="How often to check for new tasks in seconds (default: 5.0)"
    )
    
    args = parser.parse_args()
    
    service = LinguistAssistService(
        model_name=args.model,
        poll_interval=args.poll_interval
    )
    
    sys.exit(service.run())


if __name__ == "__main__":
    main()
