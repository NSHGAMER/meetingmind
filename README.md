# MeetingMind — AI Meeting Preparation Agent with Persistent Memory

> **Never walk into a meeting without remembering what happened before.**

## Problem
Professionals meet the same clients and colleagues repeatedly, yet forget what was discussed, decided and promised.
Meeting tools record and summarise single meetings; they don't connect history across meetings.

## Solution
MeetingMind remembers. After a meeting it extracts discussions, decisions, commitments and concerns from your notes,
shows them to you for **confirmation**, and stores the confirmed facts in **Hindsight** (Vectorize's agent-memory system).
Before the next meeting it **recalls** the relevant history and generates a cited briefing. It is not a chatbot or a
summariser — the persistent memory is the product.

## How it works
1. **Notes in** — type or upload `.txt/.md/.docx/.pdf`.
2. **Analyse** — LLM extracts structure. Nothing is saved yet.
3. **Confirm** — you edit/remove items; suggestions stay suggestions; status changes to existing commitments apply only if you tick them.
4. **Retain** — confirmed facts go to Hindsight (fails loudly with a 503 if Hindsight is down — never silently).
5. **Prepare** — Hindsight recall per participant + open commitments from the tracker → briefing with `[M#]/[C#]` citations back to the source meeting. Uncited history claims are stripped server-side. Retrieved facts and AI recommendations are labelled separately.
6. **Compare** — the Prepare screen can show a *generic* briefing next to the *memory-powered* one (the judges' demo moment).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Vercel Project                        │
│                                                             │
│   ┌─────────────────────────┐   ┌────────────────────────┐  │
│   │ React + TS Frontend     │   │ Python FastAPI         │  │
│   │ (Vite + Tailwind SPA)   │──>│ Serverless Function    │  │
│   │ /                       │   │ /api/* (api/index.py)  │  │
│   └─────────────────────────┘   └───────────┬────────────┘  │
└─────────────────────────────────────────────┼───────────────┘
                                              │
                      ┌───────────────────────┼───────────────────────┐
                      │                       │                       │
                      ▼                       ▼                       ▼
            ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
            │     Supabase     │    │ Hindsight Cloud  │    │     Groq LLM     │
            │    PostgreSQL    │    │ (Vectorize.io)   │    │ (openai/gpt-oss) │
            │ Relational Data  │    │ Agent Memory     │    │ High-Speed Infer │
            └──────────────────┘    └──────────────────┘    └──────────────────┘
```

## Stack
- **Frontend**: React + TypeScript + Vite + Tailwind + Lucide + Recharts
- **Backend**: FastAPI + Pydantic v2 + SQLAlchemy (running on Vercel Python Functions)
- **Database**: Supabase PostgreSQL (or local SQLite for dev)
- **Agent Memory**: Hindsight Cloud by Vectorize.io
- **AI / LLM**: Groq API

## Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/NSHGAMER/meetingmind.git
cd meetingmind

# 2. Configure environment
cp .env.example backend/.env
# Fill in your HINDSIGHT_API_KEY and LLM_API_KEY in backend/.env

# 3. Backend setup & verification
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run Hindsight smoke test
python -m scripts.hindsight_smoke_test

# Run backend test suite
python -m pytest

# Start local backend server
uvicorn app.main:app --reload --port 8000

# 4. Frontend setup
cd ../frontend
npm install
npm run dev   # Available at http://localhost:5173
```

## Production Deployment (Vercel)

MeetingMind is configured for single-click full-stack deployment on **Vercel** with **Supabase PostgreSQL**.
See complete instructions in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
