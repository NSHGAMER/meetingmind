from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, get_memory, owned
from ..errors import HindsightUnavailable
from ..models import Commitment, Contact, Insight, Meeting, User
from ..schemas import ContactIn, ContactOut
from ..services.commitments import OPEN_STATES, effective_status
from ..services.hindsight_gateway import MemoryGateway
from ..services.memory_retrieval import recall_contact

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Contact).filter(Contact.user_id == user.id).order_by(Contact.full_name).all()


@router.post("", response_model=ContactOut, status_code=201)
def create_contact(body: ContactIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = Contact(user_id=user.id, **body.model_dump())
    db.add(c)
    db.commit()
    return c


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return owned(db, Contact, contact_id, user)


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, body: ContactIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = owned(db, Contact, contact_id, user)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    db.commit()
    return c


@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = owned(db, Contact, contact_id, user)
    db.execute(
        __import__("sqlalchemy").text("DELETE FROM meeting_participants WHERE contact_id = :c"), {"c": c.id}
    )
    db.delete(c)
    db.commit()


def relationship_summary(name: str, meetings: list[Meeting], topics: Counter, open_c: list[Commitment],
                         concerns: list[Insight]) -> str:
    """Built only from real records — nothing hardcoded."""
    if not meetings:
        return f"No confirmed meeting history with {name} yet."
    n = len(meetings)
    parts = [f"{name} has participated in {n} recorded meeting{'s' if n != 1 else ''}."]
    repeated = [f"{t} ({k}x)" for t, k in topics.most_common(4) if k >= 2]
    if repeated:
        parts.append("Recurring topics: " + ", ".join(repeated) + ".")
    elif topics:
        parts.append("Topics so far: " + ", ".join(t for t, _ in topics.most_common(4)) + ".")
    if open_c:
        parts.append(f"{len(open_c)} open commitment{'s' if len(open_c) != 1 else ''}: "
                     + "; ".join(f"{c.owner_name} – {c.description}" for c in open_c[:3]) + ".")
    if concerns:
        parts.append("Concerns on record: " + "; ".join(c.text for c in concerns[:3]) + ".")
    return " ".join(parts)


@router.get("/{contact_id}/profile")
def contact_profile(contact_id: int, memory_recall: bool = True, db: Session = Depends(get_db),
                    user: User = Depends(current_user), memory: MemoryGateway = Depends(get_memory)):
    c = owned(db, Contact, contact_id, user)
    meetings = [m for m in db.query(Meeting).filter(Meeting.user_id == user.id).order_by(Meeting.scheduled_at).all()
                if any(p.id == c.id for p in m.participants)]
    history = [m for m in meetings if m.analysis_status == "confirmed"]
    hist_ids = {m.id for m in history}
    insights = [i for i in db.query(Insight).filter(Insight.user_id == user.id).all() if i.meeting_id in hist_ids]
    commitments = db.query(Commitment).filter(Commitment.user_id == user.id).all()
    mine = [x for x in commitments if x.owner_contact_id == c.id]
    open_c = [x for x in mine if x.status in OPEN_STATES]
    topics = Counter(i.topic for i in insights if i.kind == "discussion" and i.topic)
    concerns = [i for i in insights if i.kind == "concern" and (i.contact_id in (None, c.id))]
    title = {m.id: m for m in meetings}

    def ins(kind):
        return [{"text": i.text, "topic": i.topic, "meeting_id": i.meeting_id,
                 "meeting_title": title[i.meeting_id].title, "date": title[i.meeting_id].scheduled_at.isoformat()}
                for i in insights if i.kind == kind and (i.contact_id in (None, c.id) or kind in ("discussion", "decision"))]

    timeline = [{"type": "meeting", "date": m.scheduled_at.isoformat(), "title": m.title, "meeting_id": m.id,
                 "status": m.status, "confirmed": m.analysis_status == "confirmed"} for m in meetings]
    timeline += [{"type": "commitment", "date": x.created_at.isoformat(),
                  "title": f"{x.owner_name}: {x.description}", "meeting_id": x.meeting_id,
                  "status": effective_status(x)} for x in mine]
    timeline.sort(key=lambda t: t["date"])

    mem, mem_error = [], None
    if memory_recall:
        try:
            mem = [{"text": r.hit.text, "meeting_id": r.meeting_id, "type": r.hit.type}
                   for r in recall_contact(db, memory, user.id, c)]
        except HindsightUnavailable as e:
            mem_error = str(e)

    return {
        "contact": ContactOut.model_validate(c),
        "relationship_summary": relationship_summary(c.full_name, history, topics, open_c, concerns),
        "meetings": [{"id": m.id, "title": m.title, "date": m.scheduled_at.isoformat(), "status": m.status,
                      "analysis_status": m.analysis_status} for m in meetings],
        "discussions": ins("discussion"), "decisions": ins("decision"), "concerns": ins("concern"),
        "preferences": ins("preference"),
        "commitments": [{"id": x.id, "description": x.description, "owner_name": x.owner_name,
                         "due_date": x.due_date.isoformat() if x.due_date else None,
                         "status": effective_status(x), "meeting_id": x.meeting_id} for x in mine],
        "topics": [{"topic": t, "count": k} for t, k in topics.most_common()],
        "timeline": timeline,
        "hindsight_memories": mem,
        "hindsight_error": mem_error,
    }
