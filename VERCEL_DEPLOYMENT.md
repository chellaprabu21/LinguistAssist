# Deploy LinguistAssist API to Vercel (Free, No Credit Card Required)

## ✅ Prerequisites

- GitHub account
- Code pushed to: `https://github.com/chellaprabu21/LinguistAssist.git`
- Vercel account (free, no credit card needed)

---

## 🚀 Step-by-Step Deployment

### Step 1: Sign Up for Vercel

1. Go to **https://vercel.com**
2. Click **"Sign Up"** or **"Log In"**
3. Choose **"Continue with GitHub"** (recommended)
4. Authorize Vercel to access your GitHub account
5. Complete the sign-up process

**✅ No credit card required for free tier!**

---

### Step 2: Create New Project

1. In Vercel dashboard, click **"Add New..."** → **"Project"**
2. Click **"Import Git Repository"**
3. Find and select: **`chellaprabu21/LinguistAssist`**
4. Click **"Import"**

---

### Step 3: Configure Project

Vercel will auto-detect your project. Configure these settings:

#### Framework Preset:
- **Framework Preset:** `Other` (or leave as auto-detected)

#### Root Directory:
- **Root Directory:** `./` (leave as default)

#### Build and Output Settings:
- **Build Command:** (leave empty - Vercel will auto-detect)
- **Output Directory:** (leave empty)

#### Install Command:
- **Install Command:** `pip install -r requirements-cloud.txt`

---

### Step 4: Set Environment Variables

Click **"Environment Variables"** and add:

#### Required:
1. **API_KEYS**
   - **Key:** `API_KEYS`
   - **Value:** Generate a secure key:
     ```bash
     python3 -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
   - Example: `abc123xyz789...` (save this!)

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

---

### Step 5: Deploy

1. Review all settings
2. Click **"Deploy"**
3. Wait for deployment (usually 1-3 minutes)
4. Watch the build logs

---

### Step 6: Get Your API URL

Once deployed, Vercel will show:
- **Your URL:** `https://linguist-assist-api.vercel.app` (or similar)
- **Copy this URL!**

---

## 🧪 Test Your Deployment

### Health Check (No API key needed):
```bash
curl https://your-app-name.vercel.app/api/v1/health
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

### Submit a Test Task:
```bash
curl -X POST https://your-app-name.vercel.app/api/v1/tasks \
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

### Vercel Free Tier:
- ✅ **No credit card required**
- ✅ **100GB bandwidth/month**
- ✅ **100 serverless function invocations/second**
- ✅ **Automatic HTTPS**
- ✅ **Global CDN**
- ⚠️ **Serverless functions:** Cold starts possible (~1-2 seconds)
- ⚠️ **File system:** Ephemeral (SQLite database resets on each deployment)

### Database Considerations:
- **SQLite on Vercel:** Database is ephemeral (resets on redeploy)
- **Solution:** Use external database service:
  - **Supabase** (free PostgreSQL)
  - **PlanetScale** (free MySQL)
  - **MongoDB Atlas** (free tier)

### For Persistent Storage:
Consider using Vercel KV (Redis) or an external database for production use.

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

## 🔄 Auto-Deployment

Vercel automatically deploys when you push to GitHub:
- **Production:** Pushes to `main` branch
- **Preview:** Pushes to other branches create preview deployments

---

## 🆘 Troubleshooting

### Build Fails
- Check build logs in Vercel dashboard
- Verify `requirements-cloud.txt` exists
- Check Python version compatibility

### Function Timeout
- Vercel free tier: 10 seconds max execution time
- Upgrade to Pro for longer timeouts (60 seconds)

### Database Issues
- SQLite resets on each deployment (ephemeral file system)
- Use external database for persistence

### CORS Issues
- CORS is already enabled in the Flask app
- Check if your frontend domain is allowed

---

## 🎉 Success!

Your API is now live at: `https://your-app-name.vercel.app`

**Next Steps:**
- Test all endpoints
- Set up external database for persistence (optional)
- Update your Mac service to use cloud API (optional)
- Share API URL with clients/apps

---

## 📚 More Information

- Vercel Docs: https://vercel.com/docs
- Python Runtime: https://vercel.com/docs/concepts/functions/serverless-functions/runtimes/python
- Vercel Support: Available in dashboard

---

## 🔄 Alternative: Use External Database

For persistent storage, update `DATABASE_URL` to use:
- **Supabase PostgreSQL:** `postgresql://user:pass@host:5432/dbname`
- **PlanetScale MySQL:** `mysql://user:pass@host:3306/dbname`

Then update `linguist_assist_api_cloud.py` to use the appropriate database adapter.
