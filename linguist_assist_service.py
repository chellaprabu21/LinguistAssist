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

# Task queue directory
QUEUE_DIR = LOG_DIR / "queue"
QUEUE_DIR.mkdir(exist_ok=True)
PROCESSING_DIR = LOG_DIR / "processing"
PROCESSING_DIR.mkdir(exist_ok=True)
COMPLETED_DIR = LOG_DIR / "completed"
COMPLETED_DIR.mkdir(exist_ok=True)

# Service control
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    running = False


class LinguistAssistService:
    """Service daemon for LinguistAssist."""
    
    def __init__(self, model_name: str = "gemini-1.5-flash", poll_interval: float = 1.0):
        """
        Initialize the service.
        
        Args:
            model_name: Gemini model to use
            poll_interval: How often to check for new tasks (seconds)
        """
        self.model_name = model_name
        self.poll_interval = poll_interval
        self.agent = None
        logger.info(f"Initializing LinguistAssist service with model: {model_name}")
        
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
    
    def load_task(self, task_file: Path) -> Optional[Dict]:
        """Load a task from a JSON file."""
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
    
    def process_task(self, task_file: Path) -> bool:
        """
        Process a single task file.
        
        Returns:
            True if task was processed successfully, False otherwise
        """
        logger.info(f"Processing task: {task_file.name}")
        
        # Load task
        task = self.load_task(task_file)
        if not task:
            # Move to processing with error status
            try:
                task_file.rename(PROCESSING_DIR / f"{task_file.stem}_error.json")
            except:
                pass
            return False
        
        goal = task.get("goal", "")
        max_steps = task.get("max_steps", 20)
        task_id = task.get("id", task_file.stem)
        
        if not goal:
            logger.error(f"Task {task_file.name} has no goal specified")
            self.save_task_result(
                task_file,
                {"id": task_id, "status": "error", "error": "No goal specified"},
                "processing"
            )
            return False
        
        # Move task to processing directory
        try:
            processing_file = PROCESSING_DIR / task_file.name
            task_file.rename(processing_file)
            task_file = processing_file
        except Exception as e:
            logger.warning(f"Could not move task to processing: {e}")
        
        # Execute task
        try:
            logger.info(f"Executing goal: {goal} (max_steps: {max_steps})")
            success = self.agent.execute_task(goal, max_steps=max_steps)
            
            result = {
                "id": task_id,
                "goal": goal,
                "status": "completed" if success else "failed",
                "max_steps": max_steps,
                "timestamp": time.time()
            }
            
            self.save_task_result(task_file, result, "completed")
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
            self.save_task_result(task_file, result, "processing")
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
        
        logger.info("LinguistAssist service started")
        logger.info(f"Monitoring task queue: {QUEUE_DIR}")
        logger.info(f"Poll interval: {self.poll_interval} seconds")
        
        # Main loop
        while running:
            try:
                # Check for new tasks
                task_files = list(QUEUE_DIR.glob("*.json"))
                
                if task_files:
                    # Process tasks one at a time
                    task_file = task_files[0]
                    self.process_task(task_file)
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
        default=1.0,
        help="How often to check for new tasks in seconds (default: 1.0)"
    )
    
    args = parser.parse_args()
    
    service = LinguistAssistService(
        model_name=args.model,
        poll_interval=args.poll_interval
    )
    
    sys.exit(service.run())


if __name__ == "__main__":
    main()
