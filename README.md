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

## Hindsight architecture
Uses the official `hindsight-client` SDK (`create_bank`, `retain`, `recall`) only.

| Concern | Design |
|---|---|
| User isolation | One bank per user: `<prefix>-user-<id>` + tags `user:<id>` |
| Association | Tags `contact:<id>`, `meeting:<id>`; metadata `meeting_id`, `meeting_date`, `source` |
| Provenance | Every fact line carries meeting title + date; recall results map back via `document_id` |
| No duplicates | One document per meeting (`meeting-<id>`); re-confirming **replaces** its facts |
| Supersession | Status changes retain `commitment-<id>` documents saying "supersedes earlier statements" |
| Confirmed vs suggested | `CONFIRMED COMMITMENT` vs `SUGGESTION ONLY` wording; suggestions never create tracker records |
| Authoritative status | The SQLite commitment tracker decides status; memory narrates history |
| Honest stats | Memory Intelligence numbers come from a log of real retain/recall calls (`memory_events`) |

SQLite holds application records (users, contacts, meetings, commitments); long-term memory lives only in Hindsight.

## Stack
React + TypeScript + Vite + Tailwind + Lucide + Recharts · FastAPI + Pydantic + SQLAlchemy (SQLite) · Hindsight · Groq (any OpenAI-compatible LLM, configurable).

## Setup
```bash
# 1. Hindsight (pick one)
docker run --rm -it -p 8888:8888 -p 9999:9999 -e HINDSIGHT_API_LLM_API_KEY=$GROQ_KEY \
  -e HINDSIGHT_API_LLM_PROVIDER=groq -e HINDSIGHT_API_LLM_MODEL=openai/gpt-oss-20b \
  -v $HOME/.hindsight-docker:/home/hindsight/.pg0 ghcr.io/vectorize-io/hindsight:latest
#   or Hindsight Cloud: https://ui.hindsight.vectorize.io  (API URL https://api.hindsight.vectorize.io + key)

# 2. Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env            # fill LLM_API_KEY, HINDSIGHT_*, JWT_SECRET
python -m scripts.hindsight_smoke_test   # verifies a REAL Hindsight connection
uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd ../frontend && npm install && cp .env.example .env && npm run dev   # http://localhost:5173
```
Verify the Hindsight docker env-var names against the current Hindsight docs for your version.

## Environment variables
See `.env.example` (all documented). Secrets live only in `backend/.env`; the frontend only knows `VITE_API_URL`.

## Tests
```bash
cd backend && python -m pytest -q
```
Tests use an in-memory **fake** Hindsight and a deterministic **fake** LLM (`tests/fakes.py`) — they verify application logic
(flow, isolation, error handling), **not** Hindsight/LLM quality. Real-service verification: `scripts/hindsight_smoke_test.py`.

## Demo workflow
See `docs/DEMO_SCRIPT.md`. Short version: register → *Load demo data* → analyse+confirm Meeting 1 → analyse+confirm Meeting 2 → open Meeting 3 → **Compare**.

## Docs
`docs/ARCHITECTURE.md` · `docs/API.md` · `docs/DEPLOYMENT.md` · `docs/DEMO_SCRIPT.md` · `BUILD_PROGRESS.md`

## Privacy
Notes sent for analysis and recalled memories used in briefings go to the configured LLM provider. This is stated in the UI
(consent checkbox, Settings page, briefing footer). Uploads: type allow-list, 2 MB cap, text-only extraction.

## Known limitations
See `BUILD_PROGRESS.md` (audio transcription not implemented; deleting meetings doesn't purge Hindsight documents; SQLite on ephemeral hosts).
