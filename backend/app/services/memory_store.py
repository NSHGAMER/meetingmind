"""MEMORY STORAGE: turns user-CONFIRMED meeting information into Hindsight memories.

Design:
- One Hindsight bank per user (hard isolation) + tags `user:<id>`, `contact:<id>`, `meeting:<id>`.
- One Hindsight *document* per meeting (`meeting-<id>`): re-confirming a meeting replaces its facts (no duplicates).
- One document per commitment status change (`commitment-<id>`): the newest statement supersedes older ones.
- Each fact is a self-contained line carrying names and the meeting date so Hindsight's extraction keeps provenance.
- Only confirmed data is retained. Suggestions are labelled as such and never as commitments.
"""
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from ..errors import HindsightUnavailable
from ..models import Commitment, Contact, MemoryEvent, Meeting
from ..schemas import ExtractionResult
from .hindsight_gateway import MemoryGateway

log = logging.getLogger("meetingmind.store")


def _d(dt: datetime) -> str:
    return dt.strftime("%B %d, %Y")


def build_meeting_memory(meeting: Meeting, participants: list[Contact], ex: ExtractionResult) -> str:
    d = _d(meeting.scheduled_at)
    people = "; ".join(
        f"{c.full_name}" + (f" ({', '.join(x for x in [c.job_title, c.organization] if x)})" if (c.job_title or c.organization) else "")
        for c in participants
    ) or ", ".join(ex.participants)
    lines = [
        f"Meeting '{meeting.title}' (meeting ID {meeting.id}) held on {d}. Participants: {people}.",
        f"Summary of the {d} meeting: {ex.summary}",
    ]
    for x in ex.discussions:
        lines.append(f"- In the {d} meeting '{meeting.title}', discussed: {x.text}")
    for x in ex.decisions:
        lines.append(f"- Decision ({x.status}) made in the {d} meeting '{meeting.title}': {x.text}")
    for x in ex.commitments:
        due = f"due {x.due_date:%B %d, %Y}" if x.due_date else "no deadline stated"
        if x.kind == "commitment":
            lines.append(
                f"- CONFIRMED COMMITMENT (status: pending), made in the {d} meeting '{meeting.title}': "
                f"{x.owner_name} committed to {x.description}; {due}."
            )
        else:
            lines.append(
                f"- SUGGESTION ONLY (not a confirmed commitment), raised in the {d} meeting '{meeting.title}': "
                f"{x.owner_name} may {x.description}; {due}."
            )
    for x in ex.concerns:
        who = x.raised_by or "A participant"
        lines.append(f"- CONCERN raised by {who} in the {d} meeting '{meeting.title}': {x.text}")
    for x in ex.preferences:
        who = x.person or "A participant"
        lines.append(f"- PREFERENCE of {who}, stated in the {d} meeting '{meeting.title}': {x.text}")
    for x in ex.unresolved:
        lines.append(f"- UNRESOLVED as of the {d} meeting '{meeting.title}': {x}")
    for x in ex.follow_ups:
        lines.append(f"- FOLLOW-UP action agreed in the {d} meeting '{meeting.title}': {x}")
    return "\n".join(lines)


def _log(db: Session, user_id: int, kind: str, success: bool, meeting_id, contact_id, detail: str, count: int):
    db.add(MemoryEvent(user_id=user_id, kind=kind, success=success, meeting_id=meeting_id,
                       contact_id=contact_id, detail=detail[:2000], count=count))
    db.commit()


def retain_meeting(db: Session, memory: MemoryGateway, user_id: int, meeting: Meeting,
                   participants: list[Contact], ex: ExtractionResult) -> None:
    content = build_meeting_memory(meeting, participants, ex)
    tags = [f"user:{user_id}", f"meeting:{meeting.id}"] + [f"contact:{c.id}" for c in participants]
    try:
        memory.retain(
            user_id,
            content,
            document_id=f"meeting-{meeting.id}",
            tags=tags,
            context=f"Confirmed notes of meeting '{meeting.title}' on {_d(meeting.scheduled_at)}",
            timestamp=meeting.scheduled_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            metadata={"meeting_id": str(meeting.id), "meeting_date": meeting.scheduled_at.date().isoformat(),
                      "source": "confirmed_meeting_notes"},
        )
    except HindsightUnavailable as e:
        _log(db, user_id, "retain", False, meeting.id, None, f"FAILED retain meeting '{meeting.title}': {e}", 0)
        raise
    n = content.count("\n- ") + 1
    _log(db, user_id, "retain", True, meeting.id, participants[0].id if participants else None,
         f"Retained confirmed notes of '{meeting.title}' ({_d(meeting.scheduled_at)}) to Hindsight", n)


def retain_commitment_update(db: Session, memory: MemoryGateway, user_id: int, c: Commitment,
                             meeting: Meeting) -> None:
    now = datetime.utcnow()
    content = (
        f"- COMMITMENT STATUS UPDATE recorded {_d(now)}: {c.owner_name}'s commitment to {c.description} "
        f"(originally made in the {_d(meeting.scheduled_at)} meeting '{meeting.title}') is now {c.status.upper()}. "
        f"This supersedes any earlier statement about this commitment."
    )
    tags = [f"user:{user_id}", f"meeting:{meeting.id}"] + ([f"contact:{c.owner_contact_id}"] if c.owner_contact_id else [])
    try:
        memory.retain(
            user_id, content, document_id=f"commitment-{c.id}", tags=tags,
            context=f"Commitment status update for meeting '{meeting.title}'",
            timestamp=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            metadata={"meeting_id": str(meeting.id), "commitment_id": str(c.id), "status": c.status,
                      "source": "commitment_update"},
        )
    except HindsightUnavailable as e:
        _log(db, user_id, "retain", False, meeting.id, c.owner_contact_id, f"FAILED commitment update #{c.id}: {e}", 0)
        raise
    _log(db, user_id, "retain", True, meeting.id, c.owner_contact_id,
         f"Retained status update: '{c.description[:80]}' -> {c.status}", 1)
