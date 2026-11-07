"""BRIEFING GENERATION: Hindsight recall + authoritative commitment records -> cited, structured briefing.

Retrieved facts (cited [M#]/[C#]) are kept strictly apart from AI-generated recommendations. History items without a
valid citation are dropped, so the model cannot invent previous discussions.
"""
import json
import logging
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..models import Briefing, Commitment, Meeting
from .commitments import OPEN_STATES, effective_status
from .hindsight_gateway import MemoryGateway
from .llm import LLMClient
from .memory_retrieval import RecalledMemory, dedupe, recall_contact, recall_meeting_topic

log = logging.getLogger("meetingmind.briefing")
MAX_MEMORIES = 30


class CitedItem(BaseModel):
    text: str
    sources: list[str] = []


class TalkingPoint(BaseModel):
    text: str
    reason: str = ""
    sources: list[str] = []


class BriefingDraft(BaseModel):
    previous_interactions_summary: str = ""
    historical_context: list[CitedItem] = []
    previous_concerns: list[CitedItem] = []
    things_to_remember: list[CitedItem] = []
    talking_points: list[TalkingPoint] = []
    strategy: list[str] = []


MEMORY_SYSTEM = """You are MeetingMind, a meeting-preparation agent with persistent memory.
You receive (a) RECALLED MEMORIES from the user's long-term memory, each with an id like M1, and (b) OPEN COMMITMENTS
from the commitment tracker with ids like C3. The tracker is authoritative for commitment status.
Rules:
- historical_context, previous_concerns and things_to_remember may contain ONLY facts supported by the memories or
  commitments provided. Every such item MUST list the ids that support it in "sources". Never invent history.
- Mention the meeting date when a memory gives it. Distinguish confirmed commitments from suggestions.
- If memories conflict, prefer the one that is newer or marked as a status update/supersession.
- talking_points and strategy are YOUR recommendations: practical, specific, grounded in the history; cite ids in
  "sources" where they rely on a memory or commitment.
- If there is no relevant history on a point, leave the list empty rather than guessing.
JSON schema (all keys required):
{"previous_interactions_summary": str,
 "historical_context": [{"text": str, "sources": [str]}],
 "previous_concerns": [{"text": str, "sources": [str]}],
 "things_to_remember": [{"text": str, "sources": [str]}],
 "talking_points": [{"text": str, "reason": str, "sources": [str]}],
 "strategy": [str]}"""

GENERIC_SYSTEM = """You are a meeting-preparation assistant. You have NO information about any previous interactions
with these participants. Give generic, sensible preparation advice based only on the meeting title, objective and
agenda. Do NOT claim or imply any previous discussions, decisions or commitments.
JSON schema (all keys required; leave history lists empty):
{"previous_interactions_summary": "", "historical_context": [], "previous_concerns": [], "things_to_remember": [],
 "talking_points": [{"text": str, "reason": str, "sources": []}], "strategy": [str]}"""


def _meeting_ref(m: Meeting | None) -> dict | None:
    return {"id": m.id, "title": m.title, "date": m.scheduled_at.isoformat()} if m else None


def _previous_meetings(db: Session, user_id: int, meeting: Meeting) -> list[Meeting]:
    pids = {p.id for p in meeting.participants}
    rows = (
        db.query(Meeting)
        .filter(Meeting.user_id == user_id, Meeting.id != meeting.id, Meeting.analysis_status == "confirmed",
                Meeting.scheduled_at < meeting.scheduled_at)
        .order_by(Meeting.scheduled_at)
        .all()
    )
    return [m for m in rows if pids & {p.id for p in m.participants}]


def _open_commitments(db: Session, user_id: int, meeting: Meeting, prev_ids: set[int]) -> list[Commitment]:
    pids = {p.id for p in meeting.participants}
    rows = db.query(Commitment).filter(Commitment.user_id == user_id, Commitment.status.in_(OPEN_STATES)).all()
    return [c for c in rows if (c.owner_contact_id in pids) or (c.meeting_id in prev_ids)]


def generate_briefing(db: Session, memory: MemoryGateway, llm: LLMClient, user_id: int,
                      meeting: Meeting, mode: str = "memory") -> dict:
    prev = _previous_meetings(db, user_id, meeting) if mode == "memory" else []
    prev_ids = {m.id for m in prev}
    commitments = _open_commitments(db, user_id, meeting, prev_ids) if mode == "memory" else []

    recalled: list[RecalledMemory] = []
    if mode == "memory":
        for p in meeting.participants:  # raises HindsightUnavailable -> surfaced as a real integration error
            recalled += recall_contact(db, memory, user_id, p, meeting.id)
        recalled += recall_meeting_topic(db, memory, user_id, meeting)
        recalled = dedupe(recalled)[:MAX_MEMORIES]

    meetings_by_id = {m.id: m for m in db.query(Meeting).filter(Meeting.user_id == user_id).all()}
    references: dict[str, dict] = {}
    mem_lines = []
    for i, r in enumerate(recalled, 1):
        ref = f"M{i}"
        src = meetings_by_id.get(r.meeting_id) if r.meeting_id else None
        references[ref] = {"kind": "memory", "text": r.hit.text, "type": r.hit.type,
                           "source_meeting": _meeting_ref(src), "document_id": r.hit.document_id}
        when = f" [source: '{src.title}', {src.scheduled_at:%B %d, %Y}]" if src else ""
        mem_lines.append(f"[{ref}]{when} {r.hit.text}")
    com_lines = []
    commitments_out = []
    for c in commitments:
        ref = f"C{c.id}"
        src = meetings_by_id.get(c.meeting_id)
        eff = effective_status(c)
        references[ref] = {"kind": "commitment", "source_meeting": _meeting_ref(src),
                           "text": f"{c.owner_name}: {c.description}"}
        due = c.due_date.isoformat() if c.due_date else "no deadline"
        com_lines.append(f"[{ref}] {c.owner_name} committed to {c.description}; due {due}; status {eff}; "
                         f"made in '{src.title}' on {src.scheduled_at:%B %d, %Y}")
        commitments_out.append({"ref": ref, "id": c.id, "owner_name": c.owner_name, "description": c.description,
                                "due_date": c.due_date.isoformat() if c.due_date else None, "status": eff,
                                "source_meeting": _meeting_ref(src)})

    effective_mode = "memory" if (mode == "memory" and (recalled or commitments)) else "generic"
    notes: list[str] = []
    if mode == "memory" and effective_mode == "generic":
        notes.append("No confirmed history was found for these participants yet, so this is a generic briefing.")

    people = "; ".join(f"{p.full_name} ({', '.join(x for x in [p.job_title, p.organization] if x)})"
                       for p in meeting.participants) or "not specified"
    base = (f"Meeting: {meeting.title}\nWhen: {meeting.scheduled_at:%B %d, %Y %H:%M}\nParticipants: {people}\n"
            f"Objective: {meeting.objective or 'not specified'}\nAgenda: {meeting.agenda or 'not specified'}\n")
    if effective_mode == "memory":
        user_msg = (base + "\nRECALLED MEMORIES:\n" + ("\n".join(mem_lines) or "(none)") +
                    "\n\nOPEN COMMITMENTS (authoritative):\n" + ("\n".join(com_lines) or "(none)"))
        draft = llm.structured(MEMORY_SYSTEM, user_msg, BriefingDraft)
    else:
        draft = llm.structured(GENERIC_SYSTEM, base, BriefingDraft)
        draft.historical_context = draft.previous_concerns = draft.things_to_remember = []
        draft.previous_interactions_summary = ""

    valid = set(references)
    dropped = 0

    def clean(items):
        nonlocal dropped
        out = []
        for it in items:
            it.sources = [s for s in it.sources if s in valid]
            if not it.sources:  # uncited history claim -> cannot be traced -> removed
                dropped += 1
                continue
            out.append(it)
        return out

    draft.historical_context = clean(draft.historical_context)
    draft.previous_concerns = clean(draft.previous_concerns)
    draft.things_to_remember = clean(draft.things_to_remember)
    for tp in draft.talking_points:
        tp.sources = [s for s in tp.sources if s in valid]
    if dropped:
        notes.append(f"{dropped} uncited statement(s) from the model were removed.")

    result = {
        "mode": effective_mode,
        "requested_mode": mode,
        "memory_used": effective_mode == "memory",
        "memories_retrieved": len(recalled),
        "generated_at": datetime.utcnow().isoformat(),
        "overview": {
            "title": meeting.title,
            "objective": meeting.objective,
            "participants": [{"id": p.id, "name": p.full_name, "job_title": p.job_title,
                              "organization": p.organization} for p in meeting.participants],
            "previous_meetings": [_meeting_ref(m) for m in prev],
        },
        "pending_commitments": commitments_out,
        "draft": draft.model_dump(),
        "references": references,
        "notes": notes,
    }
    row = Briefing(user_id=user_id, meeting_id=meeting.id, mode=effective_mode,
                   content=json.dumps(result), memory_count=len(recalled))
    db.add(row)
    db.commit()
    result["id"] = row.id
    return result
