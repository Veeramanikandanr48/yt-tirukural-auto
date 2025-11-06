# Railway Deployment Guide - Step by Step

## Why Railway?

- ✅ No file upload size limits
- ✅ Better network (no proxy blocking)
- ✅ Easy Git deployment
- ✅ Built-in cron jobs
- ✅ $5 free credit/month

## Complete Setup Guide

### Step 1: Prepare GitHub Repository

**On your local machine:**

```bash
cd /home/finstein-emp/Downloads/ps/yt-tirukural-auto

# Initialize git (if not already)
git init

# Create .gitignore (if not exists)
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg-info/
dist/
build/
venv/
env/
.venv
*.log
temp/
data/audio_generated/
*.mp4
*.wav
token.pickle
client_secrets.json
.cache/
EOF

# Add files
git add .
git commit -m "Initial commit for Railway deployment"

# Create GitHub repo and push
# (Do this on github.com first, then:)
git remote add origin https://github.com/yourusername/yt-tirukural-auto.git
git push -u origin main
```

### Step 2: Sign Up for Railway

1. Go to: https://railway.app
2. Click **"Start a New Project"**
3. Sign up with **GitHub**
4. Authorize Railway to access your repositories

### Step 3: Deploy Your Project

1. **In Railway dashboard:**
   - Click **"New Project"**
   - Select **"Deploy from GitHub repo"**
   - Choose your `yt-tirukural-auto` repository

2. **Railway will:**
   - Auto-detect Python
   - Use your `Dockerfile` if present
   - Start building

3. **Wait for deployment** (5-10 minutes first time)

### Step 4: Configure Environment Variables

**In Railway project settings:**

Add these environment variables:
```
YOUTUBE_UPLOAD_ENABLED=true
YOUTUBE_CHANNEL_NAME=Your Channel Name
YOUTUBE_SCHEDULE_ENABLED=true
YOUTUBE_SCHEDULE_TIME=06:00
PYTHONUNBUFFERED=1
```

### Step 5: Upload Model Files

**Option A: Let Railway download automatically**

The model will download on first run (no proxy issues like PythonAnywhere).

**Option B: Upload manually via Railway CLI**

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Open shell
railway run bash

# Download model
python3 -c "from transformers import AutoTokenizer, VitsModel; AutoTokenizer.from_pretrained('facebook/mms-tts-tam'); VitsModel.from_pretrained('facebook/mms-tts-tam')"
```

### Step 6: Setup Cron Job

1. **In Railway project:**
   - Click **"New"** → **"Cron"**
   - Schedule: `0 6 * * *` (6 AM daily)
   - Command: `cd /app && python3 generate_batch_videos.py`

2. **Save and enable**

### Step 7: Upload Credentials

**For YouTube API:**

1. **Upload `client_secrets.json`:**
   - Go to Railway project → **Variables** tab
   - Add as environment variable OR
   - Use Railway's file storage

2. **Or use Railway's secrets:**
   - Add sensitive files as secrets
   - They'll be available at runtime

### Step 8: Test Deployment

**Manual trigger:**
```bash
railway run python3 generate_batch_videos.py
```

Or trigger from Railway dashboard.

## Railway Advantages Over PythonAnywhere

| Feature | PythonAnywhere | Railway |
|---------|----------------|---------|
| File upload limit | 50MB | None |
| Network access | Restricted | Full |
| Proxy issues | Yes | No |
| Model download | Blocked | Works |
| Git deployment | Manual | Automatic |
| Cron jobs | Built-in | Built-in |

## Troubleshooting

### Issue: Model download fails
**Solution:** Railway has better network - should work automatically. If not, use Railway CLI to download manually.

### Issue: Build fails
**Solution:** Check `Dockerfile` and `requirements.txt`. Railway will show build logs.

### Issue: Cron not running
**Solution:** Check cron schedule syntax and command path.

## Cost

- **Free tier:** $5 credit/month
- **Usually enough** for daily runs
- **Pay-as-you-go** after free tier

---

**Railway is the best alternative - no file size limits and better network access!**

