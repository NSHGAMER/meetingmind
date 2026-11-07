from datetime import date, datetime

from sqlalchemy.orm import Session

from ..models import Commitment, Meeting
from ..schemas import CommitmentOut

OPEN_STATES = ("pending", "in_progress")


def effective_status(c: Commitment, today: date | None = None) -> str:
    today = today or date.today()
    if c.status in OPEN_STATES and c.due_date and c.due_date < today:
        return "overdue"
    return c.status


def to_out(c: Commitment, meeting: Meeting) -> CommitmentOut:
    return CommitmentOut(
        id=c.id,
        description=c.description,
        owner_name=c.owner_name,
        owner_contact_id=c.owner_contact_id,
        meeting_id=c.meeting_id,
        meeting_title=meeting.title,
        meeting_date=meeting.scheduled_at,
        created_at=c.created_at,
        due_date=c.due_date,
        status=effective_status(c),
        stored_status=c.status,
        is_sample=c.is_sample,
    )


def list_for_user(db: Session, user_id: int, flt: str = "all") -> list[CommitmentOut]:
    rows = (
        db.query(Commitment, Meeting)
        .join(Meeting, Meeting.id == Commitment.meeting_id)
        .filter(Commitment.user_id == user_id)
        .order_by(Commitment.created_at.desc())
        .all()
    )
    out = [to_out(c, m) for c, m in rows]
    if flt == "all":
        return out
    if flt == "pending":  # open, not yet overdue
        return [c for c in out if c.status in ("pending", "in_progress")]
    return [c for c in out if c.status == flt]


def touch(c: Commitment) -> None:
    c.updated_at = datetime.utcnow()
