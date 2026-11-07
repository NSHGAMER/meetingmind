import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Briefing, Contact, Meeting, User
from ..schemas import MeetingOut
from ..services import commitments as csvc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    now = datetime.utcnow()
    meetings = db.query(Meeting).filter(Meeting.user_id == user.id).order_by(Meeting.scheduled_at).all()
    upcoming = [m for m in meetings if m.status == "scheduled" and m.scheduled_at >= now.replace(hour=0, minute=0)]
    commitments = csvc.list_for_user(db, user.id, "all")
    open_c = [c for c in commitments if c.status in ("pending", "in_progress", "overdue")]
    briefs = db.query(Briefing).filter(Briefing.user_id == user.id).order_by(Briefing.created_at.desc()).limit(5).all()
    recent = [m for m in reversed(meetings) if m.status == "completed"][:5]
    return {
        "kpis": {
            "total_meetings": len(meetings),
            "upcoming_meetings": len(upcoming),
            "total_contacts": db.query(Contact).filter(Contact.user_id == user.id).count(),
            "pending_commitments": len(open_c),
            "completed_commitments": sum(1 for c in commitments if c.status == "completed"),
        },
        "upcoming": [MeetingOut.model_validate(m).model_dump(mode="json") for m in upcoming[:6]],
        "pending_commitments": [c.model_dump(mode="json") for c in open_c[:6]],
        "recent_meetings": [MeetingOut.model_validate(m).model_dump(mode="json") for m in recent],
        "recent_briefings": [{"id": b.id, "meeting_id": b.meeting_id, "mode": b.mode,
                              "memory_count": b.memory_count, "created_at": b.created_at.isoformat(),
                              "title": json.loads(b.content)["overview"]["title"]} for b in briefs],
        "has_sample_data": any(m.is_sample for m in meetings),
    }
