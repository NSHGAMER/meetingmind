import json
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import current_user, get_llm, get_memory, owned
from ..models import Briefing, Commitment, Contact, Insight, Meeting, User
from ..schemas import AnalyzeOut, ConfirmIn, ExtractionResult, MeetingIn, MeetingOut, MeetingPatch
from ..services import briefing as briefing_svc
from ..services import documents, meeting_analysis, memory_store
from ..services.commitments import touch
from ..services.hindsight_gateway import MemoryGateway
from ..services.llm import LLMClient

log = logging.getLogger("meetingmind.meetings")
router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def _contacts(db: Session, user: User, ids: list[int]) -> list[Contact]:
    out = []
    for i in dict.fromkeys(ids):
        out.append(owned(db, Contact, i, user))  # participants must belong to the same user
    return out


def _notice(llm: LLMClient) -> str:
    d = llm.describe()
    return (f"Meeting notes are sent to the configured LLM provider ({d['provider']}, model {d['model']}) for analysis. "
            f"Only after you confirm are the extracted facts stored in your private Hindsight memory bank.")


def _match_contact(name: str | None, people: list[Contact]) -> Contact | None:
    if not name:
        return None
    n = name.strip().lower()
    for p in people:
        full = p.full_name.lower()
        if n == full or n == full.split()[0] or full.split()[0] == n.split()[0]:
            return p
    return None


@router.get("", response_model=list[MeetingOut])
def list_meetings(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = db.query(Meeting).filter(Meeting.user_id == user.id)
    if status:
        q = q.filter(Meeting.status == status)
    return q.order_by(Meeting.scheduled_at.desc()).all()


@router.post("", response_model=MeetingOut, status_code=201)
def create_meeting(body: MeetingIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = body.model_dump(exclude={"participant_ids"})
    m = Meeting(user_id=user.id, **data)
    m.participants = _contacts(db, user, body.participant_ids)
    db.add(m)
    db.commit()
    return m


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return owned(db, Meeting, meeting_id, user)


@router.patch("/{meeting_id}", response_model=MeetingOut)
def update_meeting(meeting_id: int, body: MeetingPatch, db: Session = Depends(get_db),
                   user: User = Depends(current_user)):
    m = owned(db, Meeting, meeting_id, user)
    data = body.model_dump(exclude_unset=True)
    pids = data.pop("participant_ids", None)
    for k, v in data.items():
        setattr(m, k, v)
    if pids is not None:
        m.participants = _contacts(db, user, pids)
    db.commit()
    return m


@router.delete("/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = owned(db, Meeting, meeting_id, user)
    for model in (Insight, Commitment, Briefing):
        db.query(model).filter(model.meeting_id == m.id).delete()
    m.participants = []  # ORM removes the association rows
    db.delete(m)
    db.commit()


@router.post("/{meeting_id}/notes/upload", response_model=MeetingOut)
async def upload_notes(meeting_id: int, file: UploadFile = File(...), db: Session = Depends(get_db),
                       user: User = Depends(current_user)):
    m = owned(db, Meeting, meeting_id, user)
    s = get_settings()
    data = await file.read(s.max_upload_mb * 1024 * 1024 + 1)
    m.notes = documents.extract_text(file.filename or "", data, s.max_upload_mb)
    db.commit()
    return m


@router.post("/{meeting_id}/analyze", response_model=AnalyzeOut)
def analyze(meeting_id: int, body: dict | None = None, db: Session = Depends(get_db),
            user: User = Depends(current_user), llm: LLMClient = Depends(get_llm)):
    """Extract structure from notes. Nothing is written to application records or Hindsight here."""
    m = owned(db, Meeting, meeting_id, user)
    if body and isinstance(body.get("notes"), str):
        m.notes = body["notes"][:60000]
    if not (m.notes or "").strip():
        raise HTTPException(422, "Add meeting notes (or upload a document) before analysing")
    ex = meeting_analysis.analyze_notes(db, llm, user.id, m, m.notes)
    m.analysis_json = ex.model_dump_json()
    m.analysis_status = "pending_confirmation"
    db.commit()
    return AnalyzeOut(extraction=ex, processing_notice=_notice(llm))


@router.get("/{meeting_id}/analysis", response_model=AnalyzeOut)
def get_analysis(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(current_user),
                 llm: LLMClient = Depends(get_llm)):
    m = owned(db, Meeting, meeting_id, user)
    if not m.analysis_json:
        raise HTTPException(404, "No analysis yet")
    return AnalyzeOut(extraction=ExtractionResult.model_validate_json(m.analysis_json),
                      processing_notice=_notice(llm))


@router.post("/{meeting_id}/confirm")
def confirm(meeting_id: int, body: ConfirmIn, db: Session = Depends(get_db), user: User = Depends(current_user),
            memory: MemoryGateway = Depends(get_memory)):
    """User-confirmed extraction -> Hindsight FIRST (fails loudly with 503), then application records."""
    m = owned(db, Meeting, meeting_id, user)
    ex = body.extraction
    people = list(m.participants)

    memory_store.retain_meeting(db, memory, user.id, m, people, ex)  # HindsightUnavailable -> 503, DB untouched

    # Idempotent re-confirmation: replace this meeting's insights, keep commitments that already exist
    db.query(Insight).filter(Insight.meeting_id == m.id).delete()
    existing = {(c.owner_name.lower(), c.description.lower()): c
                for c in db.query(Commitment).filter(Commitment.meeting_id == m.id).all()}
    keep = set()
    for d in ex.discussions:
        db.add(Insight(user_id=user.id, meeting_id=m.id, kind="discussion", text=d.text, topic=d.topic))
    for d in ex.decisions:
        db.add(Insight(user_id=user.id, meeting_id=m.id, kind="decision", text=d.text, topic=d.status))
    for c in ex.concerns:
        p = _match_contact(c.raised_by, people)
        db.add(Insight(user_id=user.id, meeting_id=m.id, kind="concern", text=c.text, contact_id=p.id if p else None))
    for c in ex.preferences:
        p = _match_contact(c.person, people)
        db.add(Insight(user_id=user.id, meeting_id=m.id, kind="preference", text=c.text, contact_id=p.id if p else None))
    for u in ex.unresolved:
        db.add(Insight(user_id=user.id, meeting_id=m.id, kind="unresolved", text=u))
    for c in ex.commitments:
        if c.kind == "suggestion":  # suggestions are never confirmed commitments
            db.add(Insight(user_id=user.id, meeting_id=m.id, kind="suggestion", text=f"{c.owner_name}: {c.description}"))
            continue
        key = (c.owner_name.lower(), c.description.lower())
        if key in existing:
            keep.add(existing[key].id)
            continue
        p = _match_contact(c.owner_name, people)
        db.add(Commitment(user_id=user.id, meeting_id=m.id, owner_contact_id=p.id if p else None,
                          owner_name=c.owner_name, description=c.description, due_date=c.due_date,
                          status="pending", is_sample=m.is_sample))
    for key, c in existing.items():
        if c.id not in keep and c.status == "pending":
            db.delete(c)
    m.status = "completed"
    m.analysis_status = "confirmed"
    m.analysis_json = ex.model_dump_json()
    db.commit()

    # Status updates only when the user explicitly accepted them
    warnings, applied = [], []
    suggestions = {u.commitment_id: u for u in ex.suggested_status_updates}
    for cid in body.accepted_status_update_ids:
        u = suggestions.get(cid)
        c = db.get(Commitment, cid)
        if not u or not c or c.user_id != user.id:
            continue
        c.status = u.suggested_status
        touch(c)
        db.commit()
        applied.append(cid)
        src = db.get(Meeting, c.meeting_id)
        try:
            memory_store.retain_commitment_update(db, memory, user.id, c, src)
        except Exception as e:
            warnings.append(f"Commitment #{cid} updated locally but not synced to Hindsight: {e}")
    return {"meeting": MeetingOut.model_validate(m), "applied_status_updates": applied, "warnings": warnings}


@router.post("/{meeting_id}/prepare")
def prepare(meeting_id: int, mode: str = "memory", db: Session = Depends(get_db), user: User = Depends(current_user),
            memory: MemoryGateway = Depends(get_memory), llm: LLMClient = Depends(get_llm)):
    if mode not in ("memory", "generic"):
        raise HTTPException(422, "mode must be 'memory' or 'generic'")
    m = owned(db, Meeting, meeting_id, user)
    result = briefing_svc.generate_briefing(db, memory, llm, user.id, m, mode)
    result["processing_notice"] = _notice(llm)
    return result


@router.get("/{meeting_id}/briefings")
def list_briefings(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = owned(db, Meeting, meeting_id, user)
    rows = db.query(Briefing).filter(Briefing.meeting_id == m.id).order_by(Briefing.created_at.desc()).all()
    return [{**json.loads(b.content), "id": b.id} for b in rows]
