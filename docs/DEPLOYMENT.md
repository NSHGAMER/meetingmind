# MeetingMind Production Deployment Guide (Vercel + Supabase)

MeetingMind is deployed as a single unified full-stack application on **Vercel** with **Supabase PostgreSQL** for persistent relational storage, **Hindsight Cloud** for long-term semantic memory, and **Groq** for high-speed LLM processing.

Repository: `https://github.com/NSHGAMER/meetingmind.git` (branch: `main`)

---

## Architecture Overview

- **Frontend**: React + TypeScript + Vite + Tailwind CSS (hosted statically on Vercel CDN).
- **Backend**: Python FastAPI running as Vercel Serverless Functions (`api/index.py`).
- **Relational Storage**: Supabase PostgreSQL (users, contacts, meetings, commitments, insights).
- **Agent Memory**: Hindsight Cloud by Vectorize.io (semantic retain & recall per user bank).
- **AI / LLM**: Groq API (`openai/gpt-oss-20b`).

---

## 1. Setup Supabase PostgreSQL Database

1. Sign in to [Supabase](https://supabase.com/) and click **New Project**.
2. Give your project a name (e.g. `meetingmind-db`) and set a strong database password.
3. Once the project is created, navigate to **Project Settings** -> **Database**.
4. Under **Connection string**, select **URI**:
   - For Serverless execution on Vercel, use the **Transaction Pooler** connection string (Port 6543):
     ```
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
     ```
   - Alternatively, use the direct connection string (Port 5432):
     ```
     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require
     ```
5. Copy this URI — you will paste it as `DATABASE_URL` in Vercel.
   *(Note: Tables and indexes are created automatically by SQLAlchemy on first request).*

---

## 2. Deploy Unified Project on Vercel

1. Log in to [Vercel](https://vercel.com/new).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository:
   `https://github.com/NSHGAMER/meetingmind.git`
4. Configure Project Settings:
   - **Framework Preset**: `Vite` (or `Other`)
   - **Root Directory**: `./` (leave at root — `vercel.json` and `api/index.py` orchestrate frontend and backend together)
   - **Build Command**: `npm run build` (or leave default from `vercel.json`)
   - **Output Directory**: `frontend/dist`
5. Under **Environment Variables**, add the following production variables:

| Variable | Value | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://...` | Your Supabase PostgreSQL connection URI |
| `JWT_SECRET` | `<generate-a-random-secret-string>` | 32+ character random string for JWT auth |
| `JWT_EXPIRE_MINUTES` | `1440` | Token expiration in minutes |
| `HINDSIGHT_API_URL` | `https://api.hindsight.vectorize.io` | Hindsight Cloud endpoint |
| `HINDSIGHT_API_KEY` | `<your-hindsight-cloud-api-key>` | Your Hindsight Cloud API key |
| `HINDSIGHT_BANK_PREFIX` | `meetingmind` | Memory bank prefix (isolated per user) |
| `LLM_PROVIDER` | `groq` | LLM provider |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Groq OpenAI-compatible base URL |
| `LLM_API_KEY` | `<your-groq-api-key>` | Your Groq API key |
| `LLM_MODEL` | `openai/gpt-oss-20b` | High-speed LLM model |
| `MAX_UPLOAD_MB` | `2` | Maximum file upload size in MB |
| `CORS_ORIGINS` | `https://*.vercel.app` | Allowed origins |

*(Note: `VITE_API_URL` is optional on Vercel because frontend and backend serve from the same origin; if set, set to empty or your exact Vercel URL).*

6. Click **Deploy**.
7. Vercel builds the Vite static assets, bundles the FastAPI serverless function, and assigns your production domain (`https://<project-name>.vercel.app`).

---

## 3. Verify Live Deployment

1. Visit your Vercel deployment URL (`https://<project-name>.vercel.app`).
2. Test the health check endpoint: `https://<project-name>.vercel.app/api/health` -> should return `{"status": "ok"}`.
3. In the web app:
   - Click **Register** and create an account.
   - Click **Load Demo Data** from the Dashboard (loads 3 meetings and contact).
   - Go to **Settings** -> Click **Test connection** under Hindsight Memory (verifies live Hindsight Cloud bank).
   - Go to **Meetings** -> Open Meeting 1 -> Click **Analyze Notes** -> Click **Confirm Extraction** (persists to Supabase & retains facts to Hindsight Cloud).
   - Open Meeting 3 -> Click **Prepare Meeting Briefing** with Persistent Memory (generates live briefing cited against retrieved memories).
   - Check **Memory Intelligence** to inspect the real-time audit log.
