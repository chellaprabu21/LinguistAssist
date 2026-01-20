# Step-by-Step Guide: Deploy to Render (Free)

## Prerequisites
- GitHub account
- Your code pushed to a GitHub repository

---

## Step 1: Prepare Your Code

### 1.1 Make sure you have the cloud files
Check that these files exist in your repo:
- `linguist_assist_api_cloud.py` ✅
- `requirements-cloud.txt` ✅
- `render.yaml` ✅ (optional but helpful)

### 1.2 Push to GitHub (if not already done)
```bash
cd /Users/cv/Repo/LinguistAssist

# Check git status
git status

# Add new files
git add linguist_assist_api_cloud.py requirements-cloud.txt render.yaml DEPLOYMENT_GUIDE.md RENDER_DEPLOYMENT.md

# Commit
git commit -m "Add cloud deployment files for Render"

# Push to GitHub
git push origin main
# (or git push origin master if your default branch is master)
```

---

## Step 2: Sign Up for Render

1. Go to **https://render.com**
2. Click **"Get Started for Free"** or **"Sign Up"**
3. Choose **"Sign up with GitHub"** (easiest option)
4. Authorize Render to access your GitHub account
5. Complete the sign-up process

---

## Step 3: Create a New Web Service

1. In Render dashboard, click **"New +"** button (top right)
2. Select **"Web Service"**
3. Click **"Connect account"** if prompted to connect GitHub
4. Select your GitHub repository (`LinguistAssist` or whatever it's named)
5. Click **"Connect"**

---

## Step 4: Configure Your Service

Fill in the following settings:

### Basic Settings:
- **Name:** `linguist-assist-api` (or any name you prefer)
- **Region:** Choose closest to you (e.g., `Oregon (US West)`)

### Build & Deploy:
- **Environment:** Select **`Python 3`**
- **Build Command:** 
  ```
  pip install -r requirements-cloud.txt
  ```
- **Start Command:**
  ```
  python3 linguist_assist_api_cloud.py --host 0.0.0.0 --port $PORT
  ```

### Advanced Settings (click to expand):
- **Python Version:** `3.12.0` (or latest available)

---

## Step 5: Set Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add:

### Required Variables:

1. **API_KEYS**
   - **Key:** `API_KEYS`
   - **Value:** Your API key(s) - comma-separated if multiple
   - Example: `my-secret-api-key-12345`
   - **Important:** Generate a secure key! You can use:
     ```bash
     python3 -c "import secrets; print(secrets.token_urlsafe(32))"
     ```

2. **FLASK_ENV**
   - **Key:** `FLASK_ENV`
   - **Value:** `production`

3. **DATABASE_URL** (optional - has default)
   - **Key:** `DATABASE_URL`
   - **Value:** `sqlite:///linguist_assist.db`

4. **RATE_LIMIT_RPM** (optional - defaults to 60)
   - **Key:** `RATE_LIMIT_RPM`
   - **Value:** `60`

### Example Environment Variables:
```
API_KEYS=your-generated-api-key-here
FLASK_ENV=production
DATABASE_URL=sqlite:///linguist_assist.db
RATE_LIMIT_RPM=60
```

---

## Step 6: Deploy

1. Review all your settings
2. Click **"Create Web Service"** at the bottom
3. Render will start building and deploying your app
4. Watch the build logs - it will show:
   - Installing dependencies
   - Starting your app
   - Health checks

**Build time:** Usually 2-5 minutes

---

## Step 7: Get Your API URL

Once deployed, Render will show:
- **Your URL:** `https://linguist-assist-api.onrender.com` (or similar)
- Copy this URL - you'll need it!

---

## Step 8: Test Your Deployment

### 8.1 Health Check (No API key needed)
```bash
curl https://your-app-name.onrender.com/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "LinguistAssist API",
  "version": "1.0.0-cloud",
  "database": "connected"
}
```

### 8.2 Submit a Test Task
```bash
curl -X POST https://your-app-name.onrender.com/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY_HERE" \
  -d '{
    "goal": "Test deployment",
    "max_steps": 5
  }'
```

Expected response:
```json
{
  "task_id": "uuid-here",
  "status": "queued",
  "message": "Task submitted successfully",
  "goal": "Test deployment",
  "max_steps": 5
}
```

---

## Step 9: Update Your Mac Service (Optional)

If you want your Mac service to use the cloud API instead of local files, update the API URL in your local config.

---

## Troubleshooting

### Build Fails
- Check build logs in Render dashboard
- Make sure `requirements-cloud.txt` exists
- Verify Python version compatibility

### App Crashes
- Check runtime logs in Render dashboard
- Verify environment variables are set correctly
- Make sure `API_KEYS` is set

### 502 Bad Gateway
- App might be spinning up (takes ~30s after inactivity)
- Check logs for errors
- Verify start command is correct

### Database Issues
- SQLite database is created automatically
- Check logs for database errors
- Database persists on Render's disk

---

## Important Notes

### Free Tier Limitations:
1. **Spin-down:** App sleeps after 15 minutes of inactivity
2. **Wake time:** First request after sleep takes ~30 seconds
3. **Solution:** Use a ping service (like UptimeRobot) to keep it awake, or upgrade to paid plan

### Keeping Your App Awake (Free):
You can use a free service like **UptimeRobot** to ping your health endpoint every 5 minutes:
1. Sign up at https://uptimerobot.com
2. Add a monitor for: `https://your-app.onrender.com/api/v1/health`
3. Set interval to 5 minutes

### Security:
- **Never commit API keys to GitHub!**
- Use Render's environment variables (they're encrypted)
- Rotate API keys periodically

---

## Quick Reference

### Your API Endpoints:
```
GET  /api/v1/health              - Health check (no auth)
POST /api/v1/tasks               - Submit task (requires API key)
GET  /api/v1/tasks/<id>          - Get task status (requires API key)
GET  /api/v1/tasks               - List all tasks (requires API key)
DELETE /api/v1/tasks/<id>        - Cancel task (requires API key)
```

### Example Usage:
```bash
# Set your API URL and key
export API_URL="https://your-app.onrender.com"
export API_KEY="your-api-key-here"

# Submit a task
curl -X POST $API_URL/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"goal": "Click the login button", "max_steps": 20}'

# Check task status
curl -H "X-API-Key: $API_KEY" $API_URL/api/v1/tasks/TASK_ID_HERE
```

---

## Success! 🎉

Your API is now live and accessible from anywhere!

**Next Steps:**
- Test all endpoints
- Update your Mac service to use the cloud API (optional)
- Set up monitoring/uptime checks
- Share your API URL with clients/apps

---

## Need Help?

- Render Docs: https://render.com/docs
- Render Support: Available in dashboard
- Check logs: Render dashboard → Your service → Logs tab
