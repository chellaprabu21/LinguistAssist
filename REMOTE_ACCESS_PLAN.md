# Remote Access Plan for LinguistAssist

## Overview
Enable remote triggering of LinguistAssist tasks from any device/network via HTTP API.

## Architecture

### Components
1. **HTTP API Server** - Flask/FastAPI server that accepts REST requests
2. **Authentication** - API key-based authentication for security
3. **Task Queue Integration** - Uses existing file-based queue system
4. **Remote Access Methods** - Multiple options for different use cases

### API Endpoints

```
POST   /api/v1/tasks          - Submit a new task
GET    /api/v1/tasks/<id>     - Get task status and result
GET    /api/v1/tasks           - List all tasks (queued, processing, completed)
GET    /api/v1/health          - Health check
DELETE /api/v1/tasks/<id>     - Cancel a queued task (optional)
```

### Request/Response Format

**Submit Task:**
```json
POST /api/v1/tasks
Headers: X-API-Key: <your-api-key>
Body: {
  "goal": "Log in to the website",
  "max_steps": 20
}

Response: {
  "task_id": "uuid-here",
  "status": "queued",
  "message": "Task submitted successfully"
}
```

**Get Task Status:**
```json
GET /api/v1/tasks/<task-id>
Headers: X-API-Key: <your-api-key>

Response: {
  "id": "uuid-here",
  "goal": "Log in to the website",
  "status": "completed|queued|processing|failed|error",
  "result": {...},
  "timestamp": 1234567890
}
```

## Remote Access Methods

### Option 1: SSH Tunnel (Recommended for Security)
```bash
# On remote machine
ssh -L 8080:localhost:8080 user@your-mac-ip

# Then access API at http://localhost:8080
curl -H "X-API-Key: your-key" http://localhost:8080/api/v1/tasks \
  -d '{"goal": "Click login button"}'
```

**Pros:**
- Secure (encrypted via SSH)
- No firewall changes needed
- Works from anywhere with SSH access

**Cons:**
- Requires SSH access to Mac
- Need to keep SSH tunnel active

### Option 2: Direct Network Access
```bash
# Configure API server to listen on 0.0.0.0:8080
# Access from remote machine
curl -H "X-API-Key: your-key" http://your-mac-ip:8080/api/v1/tasks \
  -d '{"goal": "Click login button"}'
```

**Pros:**
- Simple direct access
- No SSH required

**Cons:**
- Requires firewall configuration
- Less secure (should use HTTPS in production)
- Need static IP or dynamic DNS

### Option 3: VPN Access
- Connect to VPN, then access API server on local network
- Most secure for enterprise environments

### Option 4: Cloud Proxy (ngrok, Cloudflare Tunnel)
```bash
# Use ngrok to expose local API server
ngrok http 8080

# Access via ngrok URL
curl -H "X-API-Key: your-key" https://abc123.ngrok.io/api/v1/tasks \
  -d '{"goal": "Click login button"}'
```

**Pros:**
- Works behind NAT/firewall
- HTTPS included
- Easy setup

**Cons:**
- Requires third-party service
- Free tier has limitations

## Security Considerations

1. **API Key Authentication**
   - Generate unique API keys per client
   - Store keys securely (environment variable or config file)
   - Rotate keys periodically

2. **Rate Limiting**
   - Limit requests per IP/API key
   - Prevent abuse

3. **HTTPS/TLS**
   - Use reverse proxy (nginx) with SSL certificates
   - Or use ngrok/Cloudflare Tunnel for built-in HTTPS

4. **IP Whitelisting** (Optional)
   - Restrict access to known IPs
   - Useful for direct network access

5. **Input Validation**
   - Validate task goals
   - Sanitize inputs
   - Limit max_steps

## Implementation Plan

### Phase 1: Basic HTTP API Server
- [x] Create Flask/FastAPI server
- [x] Integrate with existing queue system
- [x] Add authentication middleware
- [x] Implement task submission endpoint
- [x] Implement status checking endpoint

### Phase 2: Enhanced Features
- [ ] Add task listing endpoint
- [ ] Add task cancellation
- [ ] Add rate limiting
- [ ] Add request logging
- [ ] Add health check endpoint

### Phase 3: Service Integration
- [ ] Update launchd plist to run API server
- [ ] Add API server configuration options
- [ ] Create API key management script
- [ ] Update documentation

### Phase 4: Security & Production
- [ ] Add HTTPS support (via reverse proxy)
- [ ] Add IP whitelisting option
- [ ] Add request validation
- [ ] Add monitoring/metrics

## Configuration

### API Server Config (`~/.linguist_assist/api_config.json`)
```json
{
  "host": "127.0.0.1",
  "port": 8080,
  "api_keys": [
    "your-secret-api-key-here"
  ],
  "rate_limit": {
    "enabled": true,
    "requests_per_minute": 60
  },
  "allowed_ips": []
}
```

## Usage Examples

### Python Client
```python
import requests

API_URL = "http://localhost:8080/api/v1"
API_KEY = "your-api-key"

# Submit task
response = requests.post(
    f"{API_URL}/tasks",
    json={"goal": "Log in to website", "max_steps": 20},
    headers={"X-API-Key": API_KEY}
)
task_id = response.json()["task_id"]

# Check status
status = requests.get(
    f"{API_URL}/tasks/{task_id}",
    headers={"X-API-Key": API_KEY}
)
print(status.json())
```

### cURL Examples
```bash
# Submit task
curl -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Click login button", "max_steps": 20}'

# Check status
curl -X GET http://localhost:8080/api/v1/tasks/<task-id> \
  -H "X-API-Key: your-api-key"
```

### JavaScript/Node.js Client
```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8080/api/v1';
const API_KEY = 'your-api-key';

// Submit task
const response = await axios.post(
  `${API_URL}/tasks`,
  { goal: 'Log in to website', max_steps: 20 },
  { headers: { 'X-API-Key': API_KEY } }
);

const taskId = response.data.task_id;

// Check status
const status = await axios.get(
  `${API_URL}/tasks/${taskId}`,
  { headers: { 'X-API-Key': API_KEY } }
);
```

## Next Steps
1. Implement HTTP API server
2. Add authentication
3. Integrate with service
4. Create client libraries/examples
5. Update documentation
