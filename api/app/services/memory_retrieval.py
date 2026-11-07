"""MEMORY RETRIEVAL: recalls relevant history from Hindsight for a meeting / contact. Logs every real recall."""
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..errors import HindsightUnavailable
from ..models import Contact, MemoryEvent, Meeting
from .hindsight_gateway import MemoryGateway, MemoryHit


@dataclass
class RecalledMemory:
    hit: MemoryHit
    meeting_id: int | None
    contact_id: int | None


def _meeting_id_of(hit: MemoryHit) -> int | None:
    if hit.document_id and hit.document_id.startswith("meeting-"):
        try:
            return int(hit.document_id.split("-", 1)[1])
        except ValueError:
            pass
    mid = hit.metadata.get("meeting_id")
    if mid and str(mid).isdigit():
        return int(mid)
    for t in hit.tags:
        if t.startswith("meeting:") and t.split(":", 1)[1].isdigit():
            return int(t.split(":", 1)[1])
    m = re.search(r"meeting ID (\d+)", hit.text)
    return int(m.group(1)) if m else None


def _log(db: Session, user_id: int, success: bool, meeting_id, contact_id, detail: str, count: int):
    db.add(MemoryEvent(user_id=user_id, kind="recall", success=success, meeting_id=meeting_id,
                       contact_id=contact_id, detail=detail[:2000], count=count))
    db.commit()


def recall_contact(db: Session, memory: MemoryGateway, user_id: int, contact: Contact,
                   meeting_id: int | None = None, query: str | None = None) -> list[RecalledMemory]:
    q = query or (
        f"What has {contact.full_name} discussed, decided, promised, requested or been concerned about? "
        f"Include commitments with deadlines and status, preferences and unresolved issues."
    )
    try:
        hits = memory.recall(user_id, q, tags=[f"contact:{contact.id}"], tags_match="any_strict")
    except HindsightUnavailable as e:
        _log(db, user_id, False, meeting_id, contact.id, f"FAILED recall for {contact.full_name}: {e}", 0)
        raise
    _log(db, user_id, True, meeting_id, contact.id,
         f"Recalled {len(hits)} facts about {contact.full_name} from Hindsight", len(hits))
    return [RecalledMemory(h, _meeting_id_of(h), contact.id) for h in hits]


def recall_meeting_topic(db: Session, memory: MemoryGateway, user_id: int, meeting: Meeting) -> list[RecalledMemory]:
    q = f"{meeting.title}. {meeting.objective or ''} {meeting.agenda or ''}".strip()[:600]
    try:
        hits = memory.recall(user_id, q, tags=[f"user:{user_id}"], tags_match="any_strict")
    except HindsightUnavailable as e:
        _log(db, user_id, False, meeting.id, None, f"FAILED recall for meeting objective: {e}", 0)
        raise
    _log(db, user_id, True, meeting.id, None, f"Recalled {len(hits)} facts related to '{meeting.title}'", len(hits))
    return [RecalledMemory(h, _meeting_id_of(h), None) for h in hits]


def dedupe(items: list[RecalledMemory]) -> list[RecalledMemory]:
    seen, out = set(), []
    for it in items:
        key = re.sub(r"\W+", " ", it.hit.text.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out
