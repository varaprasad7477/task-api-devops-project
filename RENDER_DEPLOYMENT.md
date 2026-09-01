# 🚀 Deploy to Render - Complete Step-by-Step Guide

**Project**: GatePulse (Task API & DevOps Project)  
**Platform**: Render.com  
**Estimated Time**: 10-15 minutes  
**Cost**: Free tier available ($0/month)

---

## ⚡ Quick Overview

Render is a modern cloud platform that:
- Deploys directly from GitHub
- No credit card needed for free tier
- Automatic SSL/HTTPS
- Supports Flask apps natively
- One-click deployments

---

## 📋 STEP 1: Create a Render Account

1. Go to **https://render.com**
2. Click **Sign up**
3. Choose **Sign up with GitHub** (recommended)
4. Authorize Render to access your GitHub account
5. Complete your account setup

---

## 🔧 STEP 2: Connect Your GitHub Repository

1. After login, go to **Dashboard** → **New** → **Web Service**
2. Click **Connect a repository**
3. Search for: `task-api-devops-project`
4. Click **Connect** next to your repository
5. Authorize Render to access the repository

---

## 📝 STEP 3: Configure Deployment Settings

After connecting repository, fill in these fields:

### Basic Configuration

| Field | Value |
|-------|-------|
| **Name** | `gatepulse` (or any name you like) |
| **Environment** | `Python 3` |
| **Region** | `Oregon (US West)` or closest to you |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -w 4 -b 0.0.0.0:$PORT app.main:create_app()` |

### Environment Variables (Optional but Recommended)

Click **Advanced** and add these:

| Variable | Value | Example |
|----------|-------|---------|
| `FLASK_ENV` | `production` | production |
| `GITHUB_TOKEN` | Your GitHub personal access token | (get from https://github.com/settings/tokens) |
| `DATABASE_URL` | Leave empty (uses SQLite) | |

**How to get GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Name: `gatepulse-render`
4. Select scopes: `repo` + `workflow`
5. Generate and copy token
6. Paste into Render environment variable

### Plan Selection

For free tier:
- Click **Free** plan
- Click **Create Web Service**

⚠️ **Note**: Free tier has limitations:
- Spins down after 15 minutes of inactivity
- Limited resources
- For production, upgrade to **Paid** plan ($7+/month)

---

## ⏳ STEP 4: Wait for Deployment

Render will:
1. Build your application (1-3 minutes)
2. Run tests (automatically, if configured)
3. Deploy to production
4. Generate a public URL like: `https://gatepulse-xyz.onrender.com`

**Monitor progress**: 
- Click **Logs** tab to watch build progress
- Wait for: `Deployed successfully` message

---

## ✅ STEP 5: Verify Deployment

After deployment succeeds, test your API:

### 1. Health Check
```bash
curl https://gatepulse-xyz.onrender.com/health
```
Expected response:
```json
{"status":"ok"}
```

### 2. Get Tasks
```bash
curl https://gatepulse-xyz.onrender.com/tasks
```

### 3. Open Dashboard
Visit: `https://gatepulse-xyz.onrender.com/dashboard`

You should see the dashboard interface!

---

## 🔄 STEP 6: Set Up Auto-Deployments (Optional)

Render automatically deploys when you push to GitHub:

1. Every `git push origin main` triggers a new build
2. If tests fail, deployment is rejected
3. You can disable this in **Service Settings** → **Auto-Deploy**

---

## 📊 STEP 7: Configure Database (Important!)

### Option A: SQLite (Default - Works on Free Tier)
- Database file is created automatically at `metrics.db`
- Data persists in Render's temporary storage
- **⚠️ Limitation**: Data is lost when service restarts

### Option B: PostgreSQL (Recommended for Production)

1. Go to **Dashboard** → **New** → **PostgreSQL**
2. Create a free PostgreSQL database
3. Copy the connection string
4. Add to Render environment variables:
   ```
   DATABASE_URL=postgresql://user:password@host:port/database
   ```

---

## 🛠️ STEP 8: Fix App for Render (If Needed)

Your app might need this modification for Render:

**Edit `app/main.py`** - Change the last lines from:
```python
if __name__ == "__main__":
    app.run(debug=True)
```

To:
```python
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
```

Then push:
```bash
git add app/main.py
git commit -m "fix: Support PORT environment variable for Render"
git push origin main
```

Render will auto-redeploy!

---

## 🔐 STEP 9: Configure Custom Domain (Optional)

To use your own domain instead of `gatepulse-xyz.onrender.com`:

1. In Render dashboard, go to **Settings**
2. Under **Custom Domains**, click **Add**
3. Enter your domain (e.g., `api.yourdomain.com`)
4. Render generates DNS instructions
5. Update your domain DNS settings
6. Wait for DNS to propagate (5-30 minutes)

---

## 📈 STEP 10: Monitor Your Deployment

### View Logs
```bash
# In Render Dashboard:
1. Click your service
2. Click "Logs" tab
3. Watch real-time logs
```

### Monitor Performance
1. Click **Metrics** tab
2. View CPU, Memory, Requests
3. Check uptime status

### Check Deployments
1. Click **Deployments** tab
2. See all deployment history
3. Rollback if needed (click three dots → Rollback)

---

## 🎯 API Endpoints (After Deployment)

Replace `https://gatepulse-xyz.onrender.com` with your actual Render URL:

### Health Check
```bash
curl https://gatepulse-xyz.onrender.com/health
```

### Get All Tasks
```bash
curl https://gatepulse-xyz.onrender.com/tasks
```

### Get Runs Summary
```bash
curl https://gatepulse-xyz.onrender.com/api/summary
```

### Get Quality Gate Status
```bash
curl https://gatepulse-xyz.onrender.com/api/quality-gate
```

### Dashboard UI
```
https://gatepulse-xyz.onrender.com/dashboard
```

### Executive Report
```
https://gatepulse-xyz.onrender.com/report
```

---

## 🆘 Troubleshooting

### Issue: "Build failed"
**Solution**: Check logs for errors
```bash
# In Render:
1. Click "Logs" tab
2. Look for red error messages
3. Fix in your code and push to GitHub
```

### Issue: "Port already in use"
**Solution**: Already fixed in start command
```
gunicorn -w 4 -b 0.0.0.0:$PORT app.main:create_app()
```

### Issue: "Service spins down"
**On free tier**: This is normal after 15 min of inactivity
**Solution**: Upgrade to paid plan, or accept cold starts

### Issue: "Database lost after restart"
**Solution**: Switch to PostgreSQL database (see Step 8)

### Issue: "404 Not Found"
**Solution**: Your API is running but route missing
```bash
# Test basic routes:
curl https://your-render-url/health
curl https://your-render-url/dashboard
```

### Issue: "CORS errors in dashboard"
**Solution**: Ensure API and frontend are on same domain (they are on Render)

---

## 💡 Best Practices

### 1. Environment Variables
Always use environment variables, never hardcode secrets:
```python
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")
```

### 2. Health Checks
Render automatically performs health checks on `/health`
- Keep this endpoint simple and fast
- Return `{"status":"ok"}` with HTTP 200

### 3. Database Persistence
- Use PostgreSQL for important data
- SQLite works but data is temporary on free tier

### 4. Monitoring
- Set up email alerts for deployment failures
- Monitor CPU/Memory in Render dashboard
- Keep logs for debugging

### 5. Auto-Redeploy on Push
- Enable in Service Settings
- Reduces manual deployment steps
- Good for continuous delivery

---

## 📊 Cost Breakdown

### Free Tier
```
✅ Price: $0/month
✅ Includes: Unlimited deployments
✅ CPU: Shared, 0.5
✅ Memory: 512 MB
⚠️ Limitation: Spins down after 15 min inactivity
⚠️ Limitation: Limited bandwidth
```

### Paid Tier (Starter)
```
✅ Price: $7/month (or more)
✅ Includes: Dedicated resources
✅ CPU: 0.5 vCPU
✅ Memory: 512 MB
✅ Benefit: Always on (no spin-down)
✅ Benefit: Better uptime SLA
```

### Add-ons
- PostgreSQL Database: Free (512 MB) or paid
- Backup: Included with PostgreSQL
- SSL/HTTPS: Always included (free)

---

## 🎯 Full Deployment Checklist

- [ ] Created Render account
- [ ] Connected GitHub repository
- [ ] Configured deployment settings
- [ ] Set environment variables (optional)
- [ ] Selected Free or Paid plan
- [ ] Deployment succeeded
- [ ] Health check works (`/health`)
- [ ] Dashboard loads (`/dashboard`)
- [ ] APIs respond correctly
- [ ] Logs show no errors
- [ ] Custom domain configured (optional)
- [ ] Monitoring set up (optional)
- [ ] Team has access to Render dashboard

---

## 🚀 Quick Command Reference

### After Render Deployment

Test your live API:
```bash
# Replace with your Render URL
RENDER_URL="https://gatepulse-xyz.onrender.com"

# Health check
curl $RENDER_URL/health

# Get tasks
curl $RENDER_URL/tasks

# Get dashboard
curl $RENDER_URL/dashboard

# Get quality gate config
curl $RENDER_URL/api/quality-gate
```

---

## 📚 Resources

| Resource | Link |
|----------|------|
| Render Docs | https://render.com/docs |
| Python on Render | https://render.com/docs/deploy-python |
| Flask Deployment | https://render.com/docs/deploy-flask |
| Environment Variables | https://render.com/docs/environment-variables |
| Custom Domains | https://render.com/docs/custom-domains |
| PostgreSQL Databases | https://render.com/docs/postgres |
| GitHub Integration | https://render.com/docs/github |

---

## ✨ Example Render Service URL

After deployment, your app is live at:

```
🌐 https://gatepulse-abc123.onrender.com
```

Share this URL with:
- ✅ Your team
- ✅ Stakeholders
- ✅ API consumers
- ✅ Documentation

---

## 🎉 SUCCESS!

Your GatePulse application is now deployed on Render!

### Next Steps
1. ✅ Monitor in Render dashboard
2. ✅ Add GitHub Personal Access Token (for GitHub API)
3. ✅ Set up custom domain (optional)
4. ✅ Configure monitoring & alerts
5. ✅ Share URL with team

**Questions?** Check Render docs or GitHub issues!

---

**Deployment Guide Created**: September 1, 2026  
**Platform**: Render.com  
**Project**: GatePulse  
**Status**: Ready for Production ✅

**Good luck! 🚀**
