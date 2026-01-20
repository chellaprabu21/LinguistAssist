#!/usr/bin/env python3
"""
Submit a task to the LinguistAssist service.
"""

import json
import sys
import time
import uuid
from pathlib import Path

# Task queue directory (same as service)
LOG_DIR = Path.home() / ".linguist_assist"
QUEUE_DIR = LOG_DIR / "queue"
QUEUE_DIR.mkdir(exist_ok=True)


def submit_task(goal: str, max_steps: int = 20, task_id: str = None) -> str:
    """
    Submit a task to the service queue.
    
    Args:
        goal: The goal to accomplish
        max_steps: Maximum number of steps
        task_id: Optional task ID (auto-generated if not provided)
    
    Returns:
        Task ID
    """
    if task_id is None:
        task_id = str(uuid.uuid4())
    
    task = {
        "id": task_id,
        "goal": goal,
        "max_steps": max_steps,
        "timestamp": time.time()
    }
    
    task_file = QUEUE_DIR / f"{task_id}.json"
    
    with open(task_file, 'w') as f:
        json.dump(task, f, indent=2)
    
    print(f"Task submitted: {task_id}")
    print(f"Goal: {goal}")
    print(f"Task file: {task_file}")
    
    return task_id


def check_task_status(task_id: str):
    """Check the status of a task."""
    completed_dir = LOG_DIR / "completed"
    processing_dir = LOG_DIR / "processing"
    
    # Check completed
    result_file = completed_dir / f"{task_id}_result.json"
    if result_file.exists():
        with open(result_file, 'r') as f:
            result = json.load(f)
        print(f"Task {task_id} status: {result.get('status', 'unknown')}")
        return result
    
    # Check processing
    result_file = processing_dir / f"{task_id}_result.json"
    if result_file.exists():
        with open(result_file, 'r') as f:
            result = json.load(f)
        print(f"Task {task_id} status: {result.get('status', 'processing')}")
        return result
    
    # Check queue
    queue_file = QUEUE_DIR / f"{task_id}.json"
    if queue_file.exists():
        print(f"Task {task_id} status: queued")
        return {"status": "queued"}
    
    print(f"Task {task_id} not found")
    return None


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Submit tasks to LinguistAssist service"
    )
    parser.add_argument(
        "goal",
        nargs="?",
        help="Goal to accomplish (if not provided, reads from stdin)"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum number of steps (default: 20)"
    )
    parser.add_argument(
        "--task-id",
        help="Optional task ID (auto-generated if not provided)"
    )
    parser.add_argument(
        "--status",
        help="Check status of a task by ID"
    )
    
    args = parser.parse_args()
    
    if args.status:
        check_task_status(args.status)
        return
    
    if args.goal:
        goal = args.goal
    else:
        # Read from stdin
        goal = sys.stdin.read().strip()
        if not goal:
            parser.error("Goal must be provided as argument or via stdin")
    
    task_id = submit_task(goal, args.max_steps, args.task_id)
    print(f"\nTo check status: python3 submit_task.py --status {task_id}")


if __name__ == "__main__":
    main()
