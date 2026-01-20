#!/usr/bin/env python3
"""
LinguistAssist GUI Application - Visual interface for submitting and monitoring tasks.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import requests
from pathlib import Path
from datetime import datetime
import time

# API Configuration
API_CONFIG_FILE = Path.home() / ".linguist_assist" / "api_config.json"
CLOUD_CONFIG_FILE = Path.home() / ".linguist_assist" / "cloud_config.json"
DEFAULT_API_URL = "http://localhost:8080"
CLOUD_API_URL = "https://linguist-assist.vercel.app"


class LinguistAssistGUI:
    """GUI application for LinguistAssist."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("LinguistAssist")
        self.root.geometry("900x700")
        
        # Load API configuration (prefer cloud config if available)
        self.api_url, self.api_key = self.load_api_config()
        
        # Task polling
        self.polling = False
        self.selected_task_id = None
        
        self.setup_ui()
        self.check_api_health()
    
    def load_api_config(self):
        """Load API URL and key from config files (prefer cloud config)."""
        # First, try cloud config
        try:
            if CLOUD_CONFIG_FILE.exists():
                with open(CLOUD_CONFIG_FILE, 'r') as f:
                    cloud_config = json.load(f)
                    api_url = cloud_config.get("api_url", CLOUD_API_URL)
                    api_key = cloud_config.get("api_key")
                    if api_key:
                        return api_url, api_key
        except Exception as e:
            print(f"Error loading cloud config: {e}")
        
        # Fall back to local config
        api_url = DEFAULT_API_URL
        api_key = None
        try:
            if API_CONFIG_FILE.exists():
                with open(API_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    api_keys = config.get("api_keys", [])
                    if api_keys:
                        api_key = api_keys[0]
        except Exception as e:
            print(f"Error loading API key: {e}")
        
        return api_url, api_key
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="LinguistAssist", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Status bar
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Left panel - Task submission
        left_panel = ttk.LabelFrame(main_frame, text="Submit Task", padding="10")
        left_panel.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_panel.columnconfigure(0, weight=1)
        
        # Goal input
        ttk.Label(left_panel, text="Goal:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.goal_entry = scrolledtext.ScrolledText(left_panel, height=4, width=40)
        self.goal_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.goal_entry.insert("1.0", "Click on the close button")
        
        # Max steps
        steps_frame = ttk.Frame(left_panel)
        steps_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(steps_frame, text="Max Steps:").pack(side=tk.LEFT, padx=(0, 5))
        self.max_steps_var = tk.StringVar(value="20")
        steps_spinbox = ttk.Spinbox(steps_frame, from_=1, to=100, textvariable=self.max_steps_var, width=10)
        steps_spinbox.pack(side=tk.LEFT)
        
        # Submit button
        submit_btn = ttk.Button(left_panel, text="Submit Task", command=self.submit_task)
        submit_btn.grid(row=3, column=0, pady=(0, 10))
        
        # API settings
        settings_frame = ttk.LabelFrame(left_panel, text="Settings", padding="10")
        settings_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        settings_frame.columnconfigure(0, weight=1)
        
        ttk.Label(settings_frame, text="API URL:").grid(row=0, column=0, sticky=tk.W)
        self.api_url_var = tk.StringVar(value=self.api_url)
        api_url_entry = ttk.Entry(settings_frame, textvariable=self.api_url_var, width=30)
        api_url_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(settings_frame, text="API Key:").grid(row=2, column=0, sticky=tk.W)
        self.api_key_var = tk.StringVar(value=self.api_key or "")
        api_key_entry = ttk.Entry(settings_frame, textvariable=self.api_key_var, show="*", width=30)
        api_key_entry.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        test_btn = ttk.Button(settings_frame, text="Test Connection", command=self.check_api_health)
        test_btn.grid(row=4, column=0)
        
        # Right panel - Task monitoring
        right_panel = ttk.LabelFrame(main_frame, text="Task Monitor", padding="10")
        right_panel.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        
        # Task list controls
        controls_frame = ttk.Frame(right_panel)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        controls_frame.columnconfigure(1, weight=1)
        
        ttk.Label(controls_frame, text="Status:").grid(row=0, column=0, padx=(0, 5))
        self.status_filter_var = tk.StringVar(value="all")
        status_combo = ttk.Combobox(controls_frame, textvariable=self.status_filter_var, 
                                     values=["all", "queued", "processing", "completed", "failed"], 
                                     state="readonly", width=15)
        status_combo.grid(row=0, column=1, padx=(0, 5))
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_task_list())
        
        refresh_btn = ttk.Button(controls_frame, text="Refresh", command=self.refresh_task_list)
        refresh_btn.grid(row=0, column=2)
        
        auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(controls_frame, text="Auto-refresh", variable=auto_refresh_var,
                                          command=self.toggle_auto_refresh)
        auto_refresh_cb.grid(row=0, column=3, padx=(10, 0))
        
        # Task list
        list_frame = ttk.Frame(right_panel)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for task list
        columns = ("ID", "Goal", "Status", "Steps", "Time")
        self.task_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.task_tree.heading(col, text=col)
            self.task_tree.column(col, width=100)
        
        self.task_tree.column("ID", width=80)
        self.task_tree.column("Goal", width=200)
        self.task_tree.column("Status", width=80)
        self.task_tree.column("Steps", width=60)
        self.task_tree.column("Time", width=120)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        
        self.task_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.task_tree.bind("<<TreeviewSelect>>", self.on_task_select)
        
        # Task details
        details_frame = ttk.LabelFrame(right_panel, text="Task Details", padding="10")
        details_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        details_frame.columnconfigure(0, weight=1)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, height=6, width=50)
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.details_text.config(state=tk.DISABLED)
        
        # Start auto-refresh if enabled
        if auto_refresh_var.get():
            self.toggle_auto_refresh()
    
    def check_api_health(self):
        """Check API health and update status."""
        try:
            self.api_url = self.api_url_var.get()
            url = f"{self.api_url}/api/v1/health"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                self.status_label.config(text="✓ API Connected", foreground="green")
                return True
            else:
                self.status_label.config(text="✗ API Error", foreground="red")
                return False
        except Exception as e:
            self.status_label.config(text=f"✗ Connection Failed: {str(e)[:30]}", foreground="red")
            return False
    
    def submit_task(self):
        """Submit a new task."""
        goal = self.goal_entry.get("1.0", tk.END).strip()
        if not goal:
            messagebox.showwarning("Warning", "Please enter a goal")
            return
        
        try:
            max_steps = int(self.max_steps_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid max steps value")
            return
        
        if not self.check_api_health():
            messagebox.showerror("Error", "Cannot connect to API. Check settings.")
            return
        
        self.api_key = self.api_key_var.get() or self.load_api_key()
        if not self.api_key:
            messagebox.showerror("Error", "API key is required")
            return
        
        # Submit task in background thread
        def submit():
            try:
                url = f"{self.api_url}/api/v1/tasks"
                headers = {
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                }
                data = {
                    "goal": goal,
                    "max_steps": max_steps
                }
                
                response = requests.post(url, json=data, headers=headers, timeout=10)
                response.raise_for_status()
                
                result = response.json()
                task_id = result.get("task_id")
                
                self.root.after(0, lambda: messagebox.showinfo("Success", 
                    f"Task submitted successfully!\nTask ID: {task_id}"))
                self.root.after(0, self.refresh_task_list)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", 
                    f"Failed to submit task: {str(e)}"))
        
        threading.Thread(target=submit, daemon=True).start()
        self.status_label.config(text="Submitting task...", foreground="blue")
    
    def refresh_task_list(self):
        """Refresh the task list."""
        if not self.check_api_health():
            return
        
        self.api_key = self.api_key_var.get() or self.load_api_key()
        if not self.api_key:
            return
        
        def fetch_tasks():
            try:
                status_filter = self.status_filter_var.get()
                url = f"{self.api_url}/api/v1/tasks"
                if status_filter != "all":
                    url += f"?status={status_filter}"
                
                headers = {"X-API-Key": self.api_key}
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                tasks = data.get("tasks", [])
                
                # Update UI in main thread
                self.root.after(0, lambda: self.update_task_list(tasks))
                
            except Exception as e:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Error fetching tasks: {str(e)[:30]}", foreground="red"))
        
        threading.Thread(target=fetch_tasks, daemon=True).start()
    
    def update_task_list(self, tasks):
        """Update the task list display."""
        # Clear existing items
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # Add tasks
        for task in tasks[:50]:  # Limit to 50 tasks
            task_id = task.get("id", "N/A")[:8]  # Short ID
            goal = task.get("goal", "N/A")[:30]  # Truncate
            status = task.get("status", "unknown")
            max_steps = task.get("max_steps", "N/A")
            
            timestamp = task.get("timestamp", 0)
            if timestamp:
                try:
                    dt = datetime.fromtimestamp(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = "N/A"
            else:
                time_str = "N/A"
            
            # Color coding
            tags = []
            if status == "completed":
                tags = ["completed"]
            elif status == "failed" or status == "error":
                tags = ["failed"]
            elif status == "processing":
                tags = ["processing"]
            elif status == "queued":
                tags = ["queued"]
            
            self.task_tree.insert("", tk.END, values=(task_id, goal, status, max_steps, time_str), 
                                 tags=tags, iid=task.get("id"))
        
        # Configure tags
        self.task_tree.tag_configure("completed", foreground="green")
        self.task_tree.tag_configure("failed", foreground="red")
        self.task_tree.tag_configure("processing", foreground="blue")
        self.task_tree.tag_configure("queued", foreground="gray")
        
        self.status_label.config(text=f"Loaded {len(tasks)} tasks", foreground="green")
    
    def on_task_select(self, event):
        """Handle task selection."""
        selection = self.task_tree.selection()
        if not selection:
            return
        
        task_id = selection[0]
        self.selected_task_id = task_id
        
        # Fetch task details
        def fetch_details():
            try:
                url = f"{self.api_url}/api/v1/tasks/{task_id}"
                headers = {"X-API-Key": self.api_key}
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                
                task = response.json()
                
                # Format details
                details = json.dumps(task, indent=2)
                
                self.root.after(0, lambda: self.update_task_details(details))
                
            except Exception as e:
                self.root.after(0, lambda: self.update_task_details(f"Error: {str(e)}"))
        
        threading.Thread(target=fetch_details, daemon=True).start()
    
    def update_task_details(self, details):
        """Update task details display."""
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert("1.0", details)
        self.details_text.config(state=tk.DISABLED)
    
    def toggle_auto_refresh(self):
        """Toggle auto-refresh."""
        if not self.polling:
            self.polling = True
            self.auto_refresh_loop()
        else:
            self.polling = False
    
    def auto_refresh_loop(self):
        """Auto-refresh loop."""
        if self.polling:
            self.refresh_task_list()
            self.root.after(5000, self.auto_refresh_loop)  # Refresh every 5 seconds


def main():
    """Main entry point."""
    root = tk.Tk()
    app = LinguistAssistGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
