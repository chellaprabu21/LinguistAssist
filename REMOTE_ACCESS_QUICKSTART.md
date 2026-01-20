# Remote Access Quick Start Guide

## 1. Setup (One-time)

```bash
# Install API server
./setup_remote_access.sh

# Get your API key
cat ~/.linguist_assist/api_config.json | grep -A 1 api_keys
```

## 2. Access Methods

### Method A: SSH Tunnel (Most Secure)

**On your Mac:**
- API server runs on `localhost:8080`

**On remote machine:**
```bash
# Create SSH tunnel
ssh -L 8080:localhost:8080 user@your-mac-ip

# In another terminal, use API
curl -H "X-API-Key: YOUR_KEY" http://localhost:8080/api/v1/tasks \
  -d '{"goal": "Log in to website"}'
```

### Method B: Direct Network Access

**On your Mac:**
```bash
# Edit config to bind to 0.0.0.0
nano ~/.linguist_assist/api_config.json
# Change "host": "127.0.0.1" to "host": "0.0.0.0"

# Restart API server
launchctl stop com.jumpcloud.linguistassist.api
launchctl start com.jumpcloud.linguistassist.api
```

**On remote machine:**
```bash
curl -H "X-API-Key: YOUR_KEY" http://YOUR_MAC_IP:8080/api/v1/tasks \
  -d '{"goal": "Log in to website"}'
```

**Note**: Configure firewall to allow port 8080.

### Method C: ngrok (Easiest, Works Behind Firewall)

**On your Mac:**
```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8080
# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

**On remote machine:**
```bash
curl -H "X-API-Key: YOUR_KEY" https://abc123.ngrok.io/api/v1/tasks \
  -d '{"goal": "Log in to website"}'
```

## 3. Common Tasks

### Submit a Task
```bash
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Log in to the website", "max_steps": 20}'
```

### Check Task Status
```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8080/api/v1/tasks/TASK_ID
```

### List All Tasks
```bash
curl -H "X-API-Key: YOUR_KEY" \
  http://localhost:8080/api/v1/tasks
```

### Cancel a Task
```bash
curl -X DELETE -H "X-API-Key: YOUR_KEY" \
  http://localhost:8080/api/v1/tasks/TASK_ID
```

## 4. Python Client

```python
from api_client_example import LinguistAssistAPIClient

# Initialize client
client = LinguistAssistAPIClient(
    "http://localhost:8080",  # or your ngrok URL
    "YOUR_API_KEY"
)

# Submit task
result = client.submit_task("Log in to website")
task_id = result["task_id"]

# Wait for completion
status = client.wait_for_task(task_id)
print(f"Status: {status['status']}")
```

## 5. Troubleshooting

### API server not running
```bash
launchctl list | grep linguistassist.api
# If not found, check logs
tail -f ~/.linguist_assist/api.log
```

### Connection refused
- Check if API server is running
- Verify host/port in config
- Check firewall settings

### Invalid API key
- Get your key: `cat ~/.linguist_assist/api_config.json`
- Generate new key: `python3 linguist_assist_api.py --generate-key`

### Rate limit exceeded
- Default: 60 requests/minute
- Edit `~/.linguist_assist/api_config.json` to adjust

## 6. Security Best Practices

1. **Use SSH tunnel** for best security
2. **Use HTTPS** (via ngrok or reverse proxy) for production
3. **Rotate API keys** periodically
4. **Use IP whitelisting** for direct network access
5. **Monitor logs** regularly: `tail -f ~/.linguist_assist/api.log`
