"""MEETING ANALYSIS + COMMITMENT EXTRACTION: notes -> structured ExtractionResult (never persisted until confirmed)."""
import json
from datetime import date

from sqlalchemy.orm import Session

from ..models import Commitment, Meeting
from ..schemas import ExtractionResult
from .commitments import OPEN_STATES
from .llm import LLMClient

SYSTEM = """You extract structured facts from meeting notes for a meeting-memory system.
Rules:
- Use ONLY what the notes say. Never invent people, numbers, dates or commitments.
- A "commitment" is an explicit promise by a named person to do something. If something is only proposed, hoped
  for or conditional ("maybe", "could", "might"), set kind to "suggestion".
- Convert deadlines to ISO dates (YYYY-MM-DD) using the meeting date for relative dates; null if none is stated.
- suggested_status_updates: ONLY if the notes clearly say an EXISTING open commitment (listed below, by id) was
  fulfilled, cancelled, or is underway. Discussing a commitment (e.g. "still pending") is NOT an update.
  Never suggest "completed" just because the item was mentioned.
- Preferences: only working/professional preferences the person voluntarily shared.
JSON schema (all keys required, use [] when empty):
{"summary": str, "participants": [str], "topics": [str],
 "discussions": [{"text": str, "topic": str|null}],
 "decisions": [{"text": str, "status": "approved"|"rejected"|"proposed"}],
 "commitments": [{"description": str, "owner_name": str, "due_date": "YYYY-MM-DD"|null,
                  "kind": "commitment"|"suggestion", "evidence": str|null}],
 "concerns": [{"text": str, "raised_by": str|null}],
 "preferences": [{"text": str, "person": str|null}],
 "unresolved": [str], "follow_ups": [str],
 "suggested_status_updates": [{"commitment_id": int, "suggested_status": "pending"|"in_progress"|"completed"|"cancelled",
                               "evidence": str|null}]}"""


def analyze_notes(db: Session, llm: LLMClient, user_id: int, meeting: Meeting, notes: str) -> ExtractionResult:
    open_commitments = (
        db.query(Commitment)
        .filter(Commitment.user_id == user_id, Commitment.status.in_(OPEN_STATES),
                Commitment.meeting_id != meeting.id)
        .all()
    )
    existing = [{"id": c.id, "owner": c.owner_name, "description": c.description,
                 "due": c.due_date.isoformat() if c.due_date else None} for c in open_commitments]
    user = (
        f"Meeting: {meeting.title}\nMeeting date: {meeting.scheduled_at.date().isoformat()}\n"
        f"Known participants: {', '.join(p.full_name for p in meeting.participants) or 'unknown'}\n"
        f"Today: {date.today().isoformat()}\n"
        f"Existing open commitments (for status-update suggestions only):\n{json.dumps(existing)}\n\n"
        f"NOTES:\n{notes}"
    )
    result = llm.structured(SYSTEM, user, ExtractionResult)
    valid_ids = {c.id for c in open_commitments}
    result.suggested_status_updates = [u for u in result.suggested_status_updates if u.commitment_id in valid_ids]
    return result
