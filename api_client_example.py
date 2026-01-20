#!/usr/bin/env python3
"""
Example client for LinguistAssist API - demonstrates remote task submission.
"""

import requests
import time
import sys
from typing import Optional, Dict


class LinguistAssistAPIClient:
    """Client for LinguistAssist HTTP API."""
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL of the API server (e.g., "http://localhost:8080")
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def submit_task(self, goal: str, max_steps: int = 20, task_id: Optional[str] = None) -> Dict:
        """
        Submit a new task.
        
        Args:
            goal: Goal to accomplish
            max_steps: Maximum number of steps
            task_id: Optional task ID (auto-generated if not provided)
        
        Returns:
            Task submission response
        """
        data = {
            "goal": goal,
            "max_steps": max_steps
        }
        if task_id:
            data["id"] = task_id
        
        response = requests.post(
            f"{self.base_url}/api/v1/tasks",
            json=data,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id: str) -> Dict:
        """
        Get task status.
        
        Args:
            task_id: Task ID
        
        Returns:
            Task status response
        """
        response = requests.get(
            f"{self.base_url}/api/v1/tasks/{task_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def list_tasks(self, status: str = "all", limit: Optional[int] = None) -> Dict:
        """
        List tasks.
        
        Args:
            status: Filter by status (all, queued, processing, completed, failed, error)
            limit: Maximum number of tasks to return
        
        Returns:
            List of tasks
        """
        params = {"status": status}
        if limit:
            params["limit"] = limit
        
        response = requests.get(
            f"{self.base_url}/api/v1/tasks",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def cancel_task(self, task_id: str) -> Dict:
        """
        Cancel a queued task.
        
        Args:
            task_id: Task ID
        
        Returns:
            Cancellation response
        """
        response = requests.delete(
            f"{self.base_url}/api/v1/tasks/{task_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_task(self, task_id: str, poll_interval: float = 2.0, timeout: Optional[float] = None) -> Dict:
        """
        Wait for a task to complete.
        
        Args:
            task_id: Task ID
            poll_interval: How often to check status (seconds)
            timeout: Maximum time to wait (None for no timeout)
        
        Returns:
            Final task status
        """
        start_time = time.time()
        
        while True:
            status = self.get_task_status(task_id)
            task_status = status.get("status")
            
            if task_status in ["completed", "failed", "error", "cancelled"]:
                return status
            
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
            
            time.sleep(poll_interval)


def main():
    """Example usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LinguistAssist API Client Example"
    )
    # Check for cloud config or environment variables
    import os
    from pathlib import Path
    
    cloud_config_file = Path.home() / ".linguist_assist" / "cloud_config.json"
    default_url = os.getenv("LINGUIST_ASSIST_API_URL", "http://localhost:8080")
    default_api_key = os.getenv("LINGUIST_ASSIST_API_KEY")
    
    # Try to load from cloud config
    if cloud_config_file.exists():
        try:
            import json
            with open(cloud_config_file, 'r') as f:
                cloud_config = json.load(f)
                default_url = cloud_config.get("api_url", default_url)
                default_api_key = cloud_config.get("api_key", default_api_key)
        except Exception:
            pass
    
    parser.add_argument(
        "--url",
        default=default_url,
        help=f"API server URL (default: {default_url})"
    )
    parser.add_argument(
        "--api-key",
        default=default_api_key,
        help="API key (can also be set via LINGUIST_ASSIST_API_KEY env var or cloud_config.json)"
    )
    parser.add_argument(
        "goal",
        nargs="?",
        help="Goal to accomplish"
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=20,
        help="Maximum steps (default: 20)"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for task to complete"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all tasks"
    )
    parser.add_argument(
        "--status",
        help="Check status of a task ID"
    )
    parser.add_argument(
        "--cancel",
        help="Cancel a task by ID"
    )
    
    args = parser.parse_args()
    
    if not args.api_key:
        parser.error("API key is required. Set --api-key, LINGUIST_ASSIST_API_KEY env var, or configure cloud_config.json")
    
    client = LinguistAssistAPIClient(args.url, args.api_key)
    
    try:
        if args.list:
            # List tasks
            result = client.list_tasks()
            print(f"Found {result['count']} tasks:")
            for task in result['tasks']:
                print(f"  {task['id']}: {task.get('status', 'unknown')} - {task.get('goal', 'N/A')}")
        
        elif args.status:
            # Check status
            status = client.get_task_status(args.status)
            print(f"Task {args.status}:")
            print(f"  Status: {status.get('status')}")
            print(f"  Goal: {status.get('goal', 'N/A')}")
            if 'error' in status:
                print(f"  Error: {status['error']}")
        
        elif args.cancel:
            # Cancel task
            result = client.cancel_task(args.cancel)
            print(f"Task {args.cancel} cancelled")
        
        elif args.goal:
            # Submit task
            result = client.submit_task(args.goal, args.max_steps)
            task_id = result['task_id']
            print(f"Task submitted: {task_id}")
            print(f"Goal: {args.goal}")
            
            if args.wait:
                print("Waiting for task to complete...")
                final_status = client.wait_for_task(task_id)
                print(f"Task completed with status: {final_status.get('status')}")
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except requests.exceptions.RequestException as e:
        print(f"API Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
