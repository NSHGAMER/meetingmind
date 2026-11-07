# Deployment

**Backend (Render)** — `render.yaml` is provided (Blueprint). Set secrets in the dashboard: `HINDSIGHT_API_KEY`, `LLM_API_KEY`, `CORS_ORIGINS` (your Vercel URL). SQLite needs the persistent disk (already declared); without a disk, data is lost on redeploy.
Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Health check: `/api/health`.

**Frontend (Vercel)** — import the repo, root directory `frontend`, framework Vite, env `VITE_API_URL=https://<your-render-service>.onrender.com`. `vercel.json` adds the SPA rewrite.

**Hindsight** — recommended for the hackathon: Hindsight Cloud (`https://api.hindsight.vectorize.io` + API key). Run `python -m scripts.hindsight_smoke_test` against it before demoing; also use Settings → *Test connection* in the app.

**Checklist**: strong `JWT_SECRET` · CORS origin set · LLM key set · smoke test passes · demo account created.
Note: Render free instances sleep; open the app once before presenting.
