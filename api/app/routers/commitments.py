from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user, get_memory, owned
from ..models import Commitment, Meeting, User
from ..schemas import CommitmentOut, CommitmentPatch, CommitmentPatchOut
from ..services import commitments as svc
from ..services import memory_store
from ..services.hindsight_gateway import MemoryGateway

router = APIRouter(prefix="/api/commitments", tags=["commitments"])


@router.get("", response_model=list[CommitmentOut])
def list_commitments(filter: str = "all", db: Session = Depends(get_db), user: User = Depends(current_user)):
    if filter not in ("all", "pending", "in_progress", "completed", "overdue", "cancelled"):
        raise HTTPException(422, "Invalid filter")
    return svc.list_for_user(db, user.id, filter)


@router.patch("/{commitment_id}", response_model=CommitmentPatchOut)
def update_commitment(commitment_id: int, body: CommitmentPatch, db: Session = Depends(get_db),
                      user: User = Depends(current_user), memory: MemoryGateway = Depends(get_memory)):
    c = owned(db, Commitment, commitment_id, user)
    meeting = db.get(Meeting, c.meeting_id)
    status_changed = body.status is not None and body.status != c.status
    if body.status is not None:
        c.status = body.status
    if body.due_date is not None:
        c.due_date = body.due_date
    if body.description:
        c.description = body.description
    svc.touch(c)
    db.commit()
    synced, err = True, None
    if status_changed:  # newer status supersedes the old one in Hindsight (same document id)
        try:
            memory_store.retain_commitment_update(db, memory, user.id, c, meeting)
        except Exception as e:  # local change stands, but we say clearly that memory was NOT updated
            synced, err = False, str(e)
    return CommitmentPatchOut(commitment=svc.to_out(c, meeting), memory_synced=synced, memory_error=err)
