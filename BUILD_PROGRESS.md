# BUILD_PROGRESS

_Last updated: 2026-11-07_

## Completed (code written)
Auth (bcrypt + JWT) · Dashboard · Contacts + profile + relationship intelligence · Meetings CRUD + multi-participant ·
Hindsight gateway/store/retrieval · LLM layer with schema validation · Note analysis + confirm flow · Commitment tracker ·
Briefing generation with citations · Memory Intelligence page · Settings/data-processing notice · Demo data loader ·
Docs (README, ARCHITECTURE, API, DEPLOYMENT, DEMO_SCRIPT) · `.env.example`, `render.yaml`, `vercel.json`.

## Tests executed
- `cd backend && python -m pytest -q` → **11 passed** (auth, contacts, meetings/participants, analysis-without-write, full 3-meeting demo incl. commitment recalled in later briefing, suggestion≠commitment, status updates need acceptance, Hindsight-down errors, user isolation, invalid LLM output, upload restrictions).
- Frontend: `npx tsc --noEmit` clean; `vite build` succeeds.
- Live smoke (uvicorn): register, demo load, dashboard OK; with no LLM key / no Hindsight server the API returned the intended clear errors (`llm_error`, `hindsight_unavailable`) from the real SDK.

## NOT verified (needs your keys)
- **Real Hindsight round-trip**: no Hindsight server or API key was available here. Tests use a fake that mimics tag/document semantics. Run `python -m scripts.hindsight_smoke_test` — this is the first thing to do.
- **Real LLM extraction/briefing quality** (Groq `openai/gpt-oss-20b` default): tests use a deterministic fake. Prompts may need tuning.
- Browser UI was type-checked and built but not exercised in a browser here.

## Known issues / limitations
- Audio transcription not implemented (optional in spec).
- Deleting a meeting/demo reset removes app records but does not delete Hindsight documents (no delete wired up).
- Hindsight retain extracts facts asynchronously; a briefing generated seconds after confirming may not yet see the new facts.
- Hindsight Docker env-var names in README should be checked against your Hindsight version.
- SQLite needs a persistent disk on Render; no migrations tool (tables auto-created).
- JWT stored in localStorage (acceptable for MVP).

## Configuration required
`LLM_API_KEY`, `HINDSIGHT_API_URL` (+ `HINDSIGHT_API_KEY` for Cloud), `JWT_SECRET`, `CORS_ORIGINS`, `VITE_API_URL`.
