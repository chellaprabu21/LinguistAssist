# Quick Start: Deploy to Render

## ✅ Pre-Deployment Checklist

- [x] Code pushed to GitHub: `https://github.com/chellaprabu21/LinguistAssist.git`
- [x] Cloud API file: `linguist_assist_api_cloud.py`
- [x] Requirements file: `requirements-cloud.txt`
- [x] Render config: `render.yaml`
- [x] Procfile: Fixed to use cloud version

---

## 🚀 Step-by-Step Deployment

### Step 1: Sign Up / Log In to Render
1. Go to **https://render.com**
2. Click **"Get Started for Free"** or **"Sign Up"**
3. Choose **"Sign up with GitHub"** (recommended)
4. Authorize Render to access your GitHub account

### Step 2: Create New Web Service
1. In Render dashboard, click **"New +"** (top right)
2. Select **"Web Service"**
3. Click **"Connect account"** if prompted
4. Select repository: **`chellaprabu21/LinguistAssist`**
5. Click **"Connect"**

### Step 3: Configure Service Settings

#### Basic Settings:
- **Name:** `linguist-assist-api` (or your preferred name)
- **Region:** Choose closest to you (e.g., `Oregon (US West)`)

#### Build & Deploy:
- **Environment:** `Python 3`
- **Branch:** `main` (or your default branch)
- **Root Directory:** (leave empty)
- **Build Command:** 
  ```
  pip install -r requirements-cloud.txt
  ```
- **Start Command:**
  ```
  python3 linguist_assist_api_cloud.py --host 0.0.0.0 --port $PORT
  ```

#### Advanced Settings:
- **Python Version:** `3.12.0` (or latest available)

### Step 4: Set Environment Variables

Click **"Advanced"** → **"Add Environment Variable"** and add:

#### Required:
1. **API_KEYS**
   - **Key:** `API_KEYS`
   - **Value:** Generate a secure key:
     ```bash
     python3 -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
   - Example: `abc123xyz789...` (save this - you'll need it!)

2. **FLASK_ENV**
   - **Key:** `FLASK_ENV`
   - **Value:** `production`

#### Optional (has defaults):
3. **DATABASE_URL**
   - **Key:** `DATABASE_URL`
   - **Value:** `sqlite:///linguist_assist.db`

4. **RATE_LIMIT_RPM**
   - **Key:** `RATE_LIMIT_RPM`
   - **Value:** `60`

### Step 5: Deploy
1. Review all settings
2. Click **"Create Web Service"** at the bottom
3. Watch the build logs (2-5 minutes)
4. Wait for deployment to complete

### Step 6: Get Your API URL
Once deployed, Render will show:
- **Your URL:** `https://linguist-assist-api.onrender.com` (or similar)
- **Copy this URL!**

### Step 7: Test Deployment

#### Health Check (No API key needed):
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

#### Submit a Test Task:
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

## 📝 Important Notes

### Free Tier Limitations:
- **Spin-down:** App sleeps after 15 minutes of inactivity
- **Wake time:** First request after sleep takes ~30 seconds
- **Solution:** Use [UptimeRobot](https://uptimerobot.com) to ping `/api/v1/health` every 5 minutes

### Security:
- ✅ Never commit API keys to GitHub
- ✅ Use Render's environment variables (encrypted)
- ✅ Rotate API keys periodically

---

## 🔗 API Endpoints

```
GET    /api/v1/health              - Health check (no auth)
POST   /api/v1/tasks               - Submit task (requires API key)
GET    /api/v1/tasks/<id>          - Get task status (requires API key)
GET    /api/v1/tasks               - List all tasks (requires API key)
DELETE /api/v1/tasks/<id>          - Cancel task (requires API key)
```

---

## 🎉 Success!

Your API is now live at: `https://your-app-name.onrender.com`

**Next Steps:**
- Test all endpoints
- Set up UptimeRobot to keep app awake (free tier)
- Update your Mac service to use cloud API (optional)
- Share API URL with clients/apps

---

## 🆘 Troubleshooting

### Build Fails
- Check build logs in Render dashboard
- Verify `requirements-cloud.txt` exists
- Check Python version compatibility

### App Crashes
- Check runtime logs in Render dashboard
- Verify `API_KEYS` environment variable is set
- Check logs for error messages

### 502 Bad Gateway
- App might be spinning up (wait ~30 seconds)
- Check logs for errors
- Verify start command is correct

---

## 📚 More Details

See `RENDER_DEPLOYMENT.md` for comprehensive guide with troubleshooting.
