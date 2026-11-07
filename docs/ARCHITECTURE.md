# Architecture

```
React SPA (Vercel) ──HTTPS/JWT──▶ FastAPI (Render)
                                    ├─ routers/      auth, contacts, meetings, commitments, memory, dashboard, demo
                                    ├─ services/
                                    │   ├─ hindsight_gateway.py   SDK wrapper (bank per user, retain, recall, ping)
                                    │   ├─ memory_store.py        MEMORY STORAGE  (confirmed facts → Hindsight documents)
                                    │   ├─ memory_retrieval.py    MEMORY RETRIEVAL (tag-scoped recall + audit log)
                                    │   ├─ llm.py                 LLM interaction (OpenAI-compatible, schema-validated, 1 repair retry)
                                    │   ├─ meeting_analysis.py    notes → ExtractionResult (+ commitment extraction)
                                    │   ├─ briefing.py            recall + tracker → cited BriefingDraft
                                    │   ├─ commitments.py         effective status (overdue), listing
                                    │   └─ documents.py           safe upload text extraction
                                    ├─ SQLite (SQLAlchemy): users, contacts, meetings, insights, commitments, briefings, memory_events
                                    └─ Hindsight (bank "<prefix>-user-<id>")
```

## Key flows
**Confirm**: `analyze` (LLM, no writes) → user edits → `confirm` → `retain_meeting` (Hindsight first; failure ⇒ 503, DB unchanged) → write insights/commitments → optional accepted status updates → `retain_commitment_update`.

**Prepare**: participants → `recall_contact` per participant (`contact:<id>`, `any_strict`) + objective recall (`user:<id>`) → dedupe → number as `M#`; open commitments from DB as `C#` → LLM → drop items without valid citations → persist briefing.

## Data isolation
Every row has `user_id`; `owned()` returns 404 for other users' rows; participants must belong to the caller; Hindsight uses a separate bank per user and tag filters.

## Failure behaviour
Hindsight down → HTTP 503 `hindsight_unavailable` (shown as an integration error); failed operations are logged and counted. LLM down/invalid → 502 `llm_error` / `llm_invalid_response`.
