# MeetingMind Deployment Guide (Vercel + Render)

This repository is ready for production deployment for your hackathon.

Repository: `https://github.com/NSHGAMER/meetingmind.git` (branch: `main`)

---

## 1. Backend Deployment (Render)

### Option A: Render Blueprint (Easiest)
1. Go to [Render Dashboard](https://dashboard.render.com/) -> **New +** -> **Blueprint**.
2. Connect your GitHub repository: `https://github.com/NSHGAMER/meetingmind.git`.
3. Render reads `render.yaml` automatically and configures `meetingmind-api`.
4. Enter the required secret environment variables:
   - `HINDSIGHT_API_KEY`: `<your-hindsight-api-key>`
   - `LLM_API_KEY`: `<your-groq-api-key>`
   - `CORS_ORIGINS`: `https://meetingmind.vercel.app` (or your Vercel deployment URL)
5. Click **Apply**.

### Option B: Manual Web Service
- **Name**: `meetingmind-api`
- **Runtime**: `Python 3`
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/health`
- **Environment Variables**:
  - `PYTHON_VERSION`: `3.12.7`
  - `DATABASE_URL`: `sqlite:///./meetingmind.db`
  - `JWT_SECRET`: `<generate-a-random-secret-string>`
  - `JWT_EXPIRE_MINUTES`: `1440`
  - `CORS_ORIGINS`: `https://your-frontend.vercel.app,http://localhost:5173`
  - `HINDSIGHT_API_URL`: `https://api.hindsight.vectorize.io`
  - `HINDSIGHT_API_KEY`: `<your-hindsight-cloud-api-key>`
  - `HINDSIGHT_BANK_PREFIX`: `meetingmind`
  - `LLM_PROVIDER`: `groq`
  - `LLM_BASE_URL`: `https://api.groq.com/openai/v1`
  - `LLM_API_KEY`: `<your-groq-api-key>`
  - `LLM_MODEL`: `openai/gpt-oss-20b`
  - `MAX_UPLOAD_MB`: `2`

---

## 2. Frontend Deployment (Vercel)

1. Go to [Vercel Dashboard](https://vercel.com/new).
2. Import the GitHub repository: `https://github.com/NSHGAMER/meetingmind.git`.
3. Configure the Project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` (or leave root as `vercel.json` at root handles both)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add Environment Variable:
   - `VITE_API_URL`: `https://meetingmind-api.onrender.com` (Your Render backend service URL without trailing slash)
5. Click **Deploy**.

---

## 3. Verify Live Deployment

1. Open your Vercel URL.
2. Register a new user account.
3. Click **Load Demo Data** on the dashboard.
4. Go to **Settings** -> Click **Test connection** under Hindsight Memory:
   - Confirms real-time connectivity to Hindsight Cloud.
5. Go to **Meetings** -> Select Meeting 3 ("Project review — ABC Technologies") -> Click **Prepare Meeting Briefing**:
   - Executes memory retrieval from Hindsight Cloud + briefing synthesis via Groq LLM.
6. Go to **Memory Intelligence** to inspect real-time audit trail and retrieved facts.
