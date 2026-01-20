# Troubleshooting Guide

## Issue: Tasks are submitted but nothing happens

### Symptoms
- Task is submitted successfully (status: "queued")
- Task is picked up by service (status changes to "processing" then "failed")
- No visual action occurs on screen

### Root Cause
The service needs **Screen Recording permissions** to:
- Take screenshots of the screen
- Detect UI elements
- Interact with the GUI

### Solution

#### Step 1: Grant Screen Recording Permissions

1. **Open System Settings** (or System Preferences on older macOS)
   - Click Apple menu > System Settings

2. **Navigate to Privacy & Security**
   - Click "Privacy & Security" in the sidebar

3. **Go to Screen Recording**
   - Scroll down and click "Screen Recording"

4. **Enable permissions for:**
   - ✅ **Python.app** (or "Python 3.12" or similar)
   - ✅ **Terminal** (if testing from terminal)

5. **Restart the service:**
   ```bash
   launchctl stop com.jumpcloud.linguistassist
   launchctl start com.jumpcloud.linguistassist
   ```

#### Step 2: Verify Permissions

Run the helper script:
```bash
./fix_permissions.sh
```

Or open System Settings directly:
```bash
open 'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'
```

#### Step 3: Test Again

```bash
API_KEY=$(cat ~/.linguist_assist/api_config.json | grep -A 1 api_keys | grep -v api_keys | head -1 | tr -d ' ,"')

curl -X POST http://localhost:8080/api/v1/tasks \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Click on the close button", "max_steps": 3}'
```

### Common Error Messages

#### "could not create image from display"
- **Cause**: Screen recording permissions not granted
- **Fix**: Grant permissions to Python.app (see above)

#### "Failed to capture screenshot"
- **Cause**: Same as above
- **Fix**: Grant screen recording permissions

#### "ModuleNotFoundError: No module named 'google'"
- **Cause**: Wrong Python interpreter being used
- **Fix**: Already fixed in plist file (uses correct Python path)

### Checking Service Status

```bash
# Check if service is running
ps aux | grep linguist_assist_service | grep -v grep

# Check service logs
tail -f ~/.linguist_assist/service.log

# Check for errors
tail -f ~/.linguist_assist/service_error.log

# Check launchctl status
launchctl list | grep linguistassist
```

### Verifying Task Processing

```bash
# Check queue
ls -lh ~/.linguist_assist/queue/

# Check processing
ls -lh ~/.linguist_assist/processing/

# Check completed (including failed tasks)
ls -lh ~/.linguist_assist/completed/ | head -10

# Check via API
API_KEY=$(cat ~/.linguist_assist/api_config.json | grep -A 1 api_keys | grep -v api_keys | head -1 | tr -d ' ,"')
curl -H "X-API-Key: $API_KEY" http://localhost:8080/api/v1/tasks | python3 -m json.tool
```

### Still Not Working?

1. **Check service is running:**
   ```bash
   launchctl start com.jumpcloud.linguistassist
   ```

2. **Check logs for errors:**
   ```bash
   tail -50 ~/.linguist_assist/service_error.log
   ```

3. **Test with a simple goal:**
   ```bash
   # Very simple task
   curl -X POST http://localhost:8080/api/v1/tasks \
     -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"goal": "Click anywhere", "max_steps": 1}'
   ```

4. **Restart everything:**
   ```bash
   launchctl stop com.jumpcloud.linguistassist
   launchctl stop com.jumpcloud.linguistassist.api
   sleep 2
   launchctl start com.jumpcloud.linguistassist.api
   launchctl start com.jumpcloud.linguistassist
   ```

### Need Help?

Check the logs:
- Service log: `~/.linguist_assist/service.log`
- Service errors: `~/.linguist_assist/service_error.log`
- API log: `~/.linguist_assist/api.log`
