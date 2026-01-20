# LinguistAssist Backend Deployment Guide

## Free Hosting Options

### Option 1: Render (Recommended) ⭐
**Best for:** Simple Flask apps with persistent storage

**Free Tier:**
- 750 hours/month (enough for 24/7)
- Persistent disk storage
- Automatic HTTPS
- Custom domains

**Setup:**
1. Sign up at https://render.com
2. Connect your GitHub repo
3. Create a new "Web Service"
4. Use these settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 linguist_assist_api.py --host 0.0.0.0 --port $PORT`
   - **Environment:** Python 3

**Pros:**
- Easy setup
- Free SSL/HTTPS
- Persistent storage
- Auto-deploys on git push

**Cons:**
- Spins down after 15 min inactivity (free tier)
- First request after spin-down takes ~30s

---

### Option 2: Railway
**Best for:** Quick deployment with minimal config

**Free Tier:**
- $5 credit/month (usually enough for small apps)
- Persistent storage
- Automatic HTTPS

**Setup:**
1. Sign up at https://railway.app
2. Click "New Project" → "Deploy from GitHub"
3. Select your repo
4. Railway auto-detects Flask apps

**Pros:**
- Very easy setup
- Good free tier
- Persistent storage

**Cons:**
- Limited free credits
- May need to upgrade for heavy use

---

### Option 3: Fly.io
**Best for:** Global distribution, low latency

**Free Tier:**
- 3 shared VMs
- 3GB persistent storage
- 160GB outbound data/month

**Setup:**
1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. Sign up: `flyctl auth signup`
3. Deploy: `flyctl launch` (in your repo directory)

**Pros:**
- Global edge locations
- Good performance
- Generous free tier

**Cons:**
- More complex setup
- Requires Docker knowledge

---

### Option 4: PythonAnywhere
**Best for:** Python-focused hosting

**Free Tier:**
- 1 web app
- 512MB disk space
- Limited CPU time

**Setup:**
1. Sign up at https://www.pythonanywhere.com
2. Upload your files via web interface
3. Configure web app to run your Flask app

**Pros:**
- Python-focused
- Easy file management
- Built-in console

**Cons:**
- Limited free tier
- Can only access from whitelisted domains

---

## Important: File Storage Adaptation

⚠️ **Current Issue:** Your API uses local file storage (`~/.linguist_assist/queue/`), which won't work on cloud platforms.

### Solution Options:

#### Option A: Use SQLite Database (Easiest)
Replace file-based storage with SQLite. Works on all platforms.

#### Option B: Use PostgreSQL (Better for production)
Use a free PostgreSQL database (Render, Railway, Supabase all offer free tiers).

#### Option C: Use Cloud Storage
Use S3-compatible storage (Backblaze B2 has free tier).

---

## Quick Start: Deploy to Render

### Step 1: Create `render.yaml` (optional)

```yaml
services:
  - type: web
    name: linguist-assist-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python3 linguist_assist_api.py --host 0.0.0.0 --port $PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.0
```

### Step 2: Adapt for Cloud Storage

You'll need to modify `linguist_assist_api.py` to use a database instead of files. See the next section.

### Step 3: Deploy

1. Push your code to GitHub
2. Go to Render dashboard
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Render will auto-detect settings
6. Add environment variable: `PORT` (Render sets this automatically)
7. Deploy!

---

## Code Changes Needed for Cloud Deployment

### Minimal Changes (SQLite)

Replace file operations with SQLite database operations. I can help you create an adapted version.

### Required Changes:

1. **Database instead of files:**
   - Replace `QUEUE_DIR`, `PROCESSING_DIR`, `COMPLETED_DIR` with database tables
   - Use SQLite (included with Python) or PostgreSQL

2. **Environment variables:**
   - Use `os.getenv('PORT', 8080)` for port
   - Store API keys in environment variables (not files)

3. **CORS configuration:**
   - Update CORS to allow your frontend domain

---

## Environment Variables to Set

```bash
# API Configuration
PORT=8080  # Usually set automatically by hosting platform
FLASK_ENV=production

# Optional: Store API keys in env vars instead of files
API_KEYS=key1,key2,key3
```

---

## Testing Your Deployment

Once deployed, test with:

```bash
# Health check (no auth needed)
curl https://your-app.onrender.com/api/v1/health

# Submit task (replace with your API key)
curl -X POST https://your-app.onrender.com/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"goal": "Test task", "max_steps": 10}'
```

---

## Next Steps

1. **Choose a hosting platform** (Render recommended)
2. **Adapt code for cloud storage** (I can help create a database version)
3. **Deploy and test**
4. **Update your Mac service** to poll the cloud API instead of local files

Would you like me to:
- Create a cloud-ready version with SQLite database?
- Set up deployment files for a specific platform?
- Help adapt the Mac service to work with the cloud API?
