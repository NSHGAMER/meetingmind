"""Demo data: raw records only (contact, meetings, notes). Extraction, memory and briefings are produced live."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Briefing, Commitment, Contact, Insight, Meeting, User

router = APIRouter(prefix="/api/demo", tags=["demo"])

NOTES_1 = """Kickoff call with Robert (Sales Manager, ABC Technologies) about the customer portal project.
- Robert confirmed the project budget is Rs 5 lakh (₹5,00,000).
- Delivery requirement: the full project must be delivered within 60 days of kickoff.
- Robert prefers monthly payments instead of milestone-based payments.
- Robert promised to send the detailed requirements document by October 25.
- I will prepare a draft proposal once the requirements document arrives."""

NOTES_2 = """Follow-up call with Robert from ABC Technologies.
- The requirements document has still not been received; Robert said it is still pending on his side.
- Robert expressed concern that the 60-day delivery timeline is too tight given the scope.
- Robert asked for a revised project timeline before the next meeting.
- I agreed to send the revised project timeline by November 10.
- Payment terms were not discussed again."""


@router.post("/load")
def load_demo(db: Session = Depends(get_db), user: User = Depends(current_user)):
    existing = db.query(Contact).filter(Contact.user_id == user.id, Contact.is_sample.is_(True)).first()
    if existing:
        return {"loaded": False, "message": "Demo data already loaded"}
    year = datetime.utcnow().year
    robert = Contact(user_id=user.id, full_name="Robert Mehta", email="robert@abctech.example",
                     organization="ABC Technologies", job_title="Sales Manager",
                     description="Primary buyer-side contact for the customer portal project.",
                     relationship_notes="Direct, prefers short updates.", is_sample=True)
    db.add(robert)
    db.flush()
    specs = [
        ("Project kickoff – ABC Technologies", datetime(year, 10, 20, 10, 0), "completed", NOTES_1,
         "Understand scope, budget and delivery expectations."),
        ("Project follow-up – requirements & timeline", datetime(year, 10, 27, 10, 0), "completed", NOTES_2,
         "Review progress on requirements and timeline."),
        ("Project review – ABC Technologies", datetime.utcnow().replace(hour=11, minute=0, second=0, microsecond=0)
         + timedelta(days=5), "scheduled", None,
         "Agree revised delivery timeline and unblock requirements."),
    ]
    ids = []
    for title, when, status, notes, objective in specs:
        m = Meeting(user_id=user.id, title=title, organization="ABC Technologies", scheduled_at=when,
                    status=status, notes=notes, objective=objective, is_sample=True,
                    agenda="Requirements status\nDelivery timeline\nPayment arrangement")
        m.participants = [robert]
        db.add(m)
        db.flush()
        ids.append(m.id)
    db.commit()
    return {"loaded": True, "contact_id": robert.id, "meeting_ids": ids}


@router.delete("/reset")
def reset_demo(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Removes sample application records. (Facts already retained in Hindsight stay in your memory bank.)"""
    mids = [m.id for m in db.query(Meeting).filter(Meeting.user_id == user.id, Meeting.is_sample.is_(True)).all()]
    if mids:
        for model in (Insight, Commitment, Briefing):
            db.query(model).filter(model.meeting_id.in_(mids)).delete(synchronize_session=False)
        db.execute(text("DELETE FROM meeting_participants WHERE meeting_id IN (%s)" % ",".join(map(str, mids))))
        db.query(Meeting).filter(Meeting.id.in_(mids)).delete(synchronize_session=False)
    cids = [c.id for c in db.query(Contact).filter(Contact.user_id == user.id, Contact.is_sample.is_(True)).all()]
    if cids:
        db.query(Contact).filter(Contact.id.in_(cids)).delete(synchronize_session=False)
    db.commit()
    return {"removed_meetings": len(mids), "removed_contacts": len(cids)}
