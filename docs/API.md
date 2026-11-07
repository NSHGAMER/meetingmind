# API (interactive docs at `/docs` when running)

All routes except register/login/health need `Authorization: Bearer <token>`.

| Method & path | Purpose |
|---|---|
| POST `/api/auth/register`, `/api/auth/login` | → `{access_token, user}` |
| GET `/api/auth/me` · POST `/api/auth/logout` | session |
| GET/POST `/api/contacts` · GET/PUT/DELETE `/api/contacts/{id}` | contacts |
| GET `/api/contacts/{id}/profile` | relationship intelligence, history, live Hindsight recall |
| GET/POST `/api/meetings` · GET/PATCH/DELETE `/api/meetings/{id}` | meetings (multi-participant) |
| POST `/api/meetings/{id}/notes/upload` | `.txt .md .docx .pdf`, ≤ MAX_UPLOAD_MB |
| POST `/api/meetings/{id}/analyze` | extract (no writes) |
| GET `/api/meetings/{id}/analysis` | pending extraction |
| POST `/api/meetings/{id}/confirm` | `{extraction, accepted_status_update_ids}` → Hindsight + records |
| POST `/api/meetings/{id}/prepare?mode=memory\|generic` | briefing |
| GET `/api/meetings/{id}/briefings` | history |
| GET `/api/commitments?filter=all\|pending\|completed\|overdue\|in_progress\|cancelled` | tracker |
| PATCH `/api/commitments/{id}` | status/due/description; returns `memory_synced` |
| GET `/api/dashboard` | KPIs & lists |
| GET `/api/memory/overview` | Memory Intelligence data |
| GET `/api/memory/health` | live Hindsight probe |
| GET `/api/settings/info` | endpoints & data-processing notice |
| POST `/api/demo/load` · DELETE `/api/demo/reset` | sample data |

Errors: `{detail, code?}` — codes `hindsight_unavailable` (503), `llm_error` / `llm_invalid_response` (502).
