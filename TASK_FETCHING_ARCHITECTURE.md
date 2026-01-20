# Task Fetching Architecture

## Current Implementation: File-Based Queue with Polling

The LinguistAssist service uses a **file-based queue system** with **polling** to fetch tasks. Here's how it works:

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   API Server    │         │   File System    │         │  Service Daemon │
│  (HTTP API)     │────────▶│   Queue Dir      │◀────────│  (Worker)       │
│                 │  Write  │  ~/.linguist_    │  Poll   │                 │
│  submit_task.py │         │  assist/queue/   │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                    │
                                    │ File Operations
                                    ▼
                            ┌──────────────────┐
                            │ Processing Dir   │
                            │  (in-progress)   │
                            └──────────────────┘
                                    │
                                    ▼
                            ┌──────────────────┐
                            │ Completed Dir    │
                            │  (results)       │
                            └──────────────────┘
```

## How Tasks Are Fetched

### 1. Task Submission (Producer)

**API Server** (`linguist_assist_api.py`):
```python
# When a task is submitted via HTTP API
task_file = QUEUE_DIR / f"{task_id}.json"
with open(task_file, 'w') as f:
    json.dump(task, f, indent=2)
```

**Local Script** (`submit_task.py`):
```python
# Same mechanism - writes JSON file to queue directory
task_file = QUEUE_DIR / f"{task_id}.json"
with open(task_file, 'w') as f:
    json.dump(task, f, indent=2)
```

**Result**: A JSON file is created in `~/.linguist_assist/queue/` directory.

### 2. Task Fetching (Consumer)

**Service Daemon** (`linguist_assist_service.py`):

```python
# Main service loop (lines 192-203)
while running:
    try:
        # POLLING: Check for new tasks every poll_interval seconds
        task_files = list(QUEUE_DIR.glob("*.json"))
        
        if task_files:
            # Found a task - process the first one
            task_file = task_files[0]
            self.process_task(task_file)
        else:
            # No tasks - sleep and poll again
            time.sleep(self.poll_interval)  # Default: 1.0 seconds
```

**Key Points**:
- **Polling Interval**: Default is 1.0 second (configurable via `--poll-interval`)
- **File Pattern**: Looks for `*.json` files in the queue directory
- **Processing Order**: Processes tasks in filesystem order (first file found)
- **Sequential Processing**: Only one task at a time (no parallel execution)

### 3. Task Processing Flow

```
1. Service polls QUEUE_DIR
   ↓
2. Finds task file (e.g., "abc-123.json")
   ↓
3. Loads JSON: {"id": "abc-123", "goal": "...", "max_steps": 20}
   ↓
4. Moves file: queue/abc-123.json → processing/abc-123.json
   ↓
5. Executes task: agent.execute_task(goal, max_steps)
   ↓
6. Saves result: processing/abc-123_result.json
   ↓
7. Moves to completed: processing/abc-123.json → completed/abc-123.json
```

## Code Flow

### Service Daemon Main Loop

```python
# linguist_assist_service.py, lines 174-214

def run(self):
    """Main service loop."""
    # Initialize agent
    self.initialize_agent()
    
    logger.info(f"Monitoring task queue: {QUEUE_DIR}")
    logger.info(f"Poll interval: {self.poll_interval} seconds")
    
    # Main polling loop
    while running:
        try:
            # STEP 1: Poll the queue directory
            task_files = list(QUEUE_DIR.glob("*.json"))
            
            if task_files:
                # STEP 2: Pick first task file
                task_file = task_files[0]
                
                # STEP 3: Process it
                self.process_task(task_file)
            else:
                # STEP 4: No tasks - sleep and poll again
                time.sleep(self.poll_interval)
```

### Task Processing

```python
# linguist_assist_service.py, lines 105-172

def process_task(self, task_file: Path) -> bool:
    # Load task from JSON file
    task = self.load_task(task_file)
    
    # Extract task details
    goal = task.get("goal", "")
    max_steps = task.get("max_steps", 20)
    task_id = task.get("id", task_file.stem)
    
    # Move to processing directory (prevents re-processing)
    processing_file = PROCESSING_DIR / task_file.name
    task_file.rename(processing_file)
    
    # Execute the task
    success = self.agent.execute_task(goal, max_steps=max_steps)
    
    # Save result and move to completed
    result = {
        "id": task_id,
        "goal": goal,
        "status": "completed" if success else "failed",
        "timestamp": time.time()
    }
    self.save_task_result(processing_file, result, "completed")
```

## Directory Structure

```
~/.linguist_assist/
├── queue/              # New tasks waiting to be processed
│   ├── task-1.json
│   └── task-2.json
│
├── processing/         # Tasks currently being processed
│   ├── task-3.json
│   └── task-3_result.json
│
├── completed/         # Finished tasks with results
│   ├── task-1.json
│   ├── task-1_result.json
│   └── task-2_result.json
│
└── api_config.json     # API server configuration
```

## Characteristics

### Advantages
- ✅ **Simple**: No database or message queue required
- ✅ **Reliable**: File system is durable
- ✅ **Debuggable**: Can inspect queue files directly
- ✅ **Stateless**: Service can restart without losing tasks
- ✅ **Cross-platform**: Works on any OS with file system

### Limitations
- ⚠️ **Polling Overhead**: Checks directory every second (even when idle)
- ⚠️ **No Priority**: Processes tasks in filesystem order
- ⚠️ **Sequential**: Only one task at a time
- ⚠️ **File System Dependent**: Performance limited by disk I/O
- ⚠️ **No Real-time**: Up to `poll_interval` delay before task is picked up

## Performance Characteristics

- **Latency**: Task picked up within `poll_interval` seconds (default: 1s)
- **Throughput**: One task at a time, sequential processing
- **Scalability**: Limited by single worker, file system I/O

## Alternative Approaches (Future Enhancements)

### Option 1: File System Events (Watchdog)
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# React immediately when file is created
# Instead of polling every second
```

### Option 2: Message Queue (Redis/RabbitMQ)
```python
# Use Redis/RabbitMQ for better scalability
import redis
r = redis.Redis()
r.lpush('tasks', json.dumps(task))
```

### Option 3: Database Queue
```python
# Use SQLite/PostgreSQL for task queue
# Better querying, priority, and status tracking
```

### Option 4: HTTP Push (Webhooks)
```python
# Service exposes HTTP endpoint
# API server pushes tasks directly to service
# No polling needed
```

## Configuration

The polling interval can be configured:

```bash
# Via command line
python3 linguist_assist_service.py --poll-interval 0.5

# Via launchd plist
<key>ProgramArguments</key>
<array>
    <string>--poll-interval</string>
    <string>0.5</string>
</array>
```

## Monitoring

Check queue status:
```bash
# Count queued tasks
ls -1 ~/.linguist_assist/queue/*.json | wc -l

# List queued tasks
ls -lh ~/.linguist_assist/queue/

# Check processing
ls -lh ~/.linguist_assist/processing/

# View recent completions
ls -lht ~/.linguist_assist/completed/ | head -10
```

## Summary

The service uses **file system polling** to fetch tasks:
1. Tasks are written as JSON files to `~/.linguist_assist/queue/`
2. Service daemon polls this directory every `poll_interval` seconds
3. When a task file is found, it's loaded, processed, and moved through directories
4. Results are saved alongside task files in the `completed/` directory

This is a simple, reliable approach suitable for single-worker scenarios. For higher throughput or lower latency, consider implementing file system events or a message queue.
