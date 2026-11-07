import json
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..deps import current_user, get_llm, get_memory
from ..models import Briefing, Commitment, Contact, Insight, MemoryEvent, Meeting, User
from ..services import commitments as csvc
from ..services.hindsight_gateway import MemoryGateway
from ..services.llm import LLMClient

router = APIRouter(prefix="/api", tags=["memory"])


@router.get("/memory/health")
def hindsight_health(user: User = Depends(current_user), memory: MemoryGateway = Depends(get_memory)):
    """Real connectivity probe against Hindsight (HindsightUnavailable -> 503 with a clear message)."""
    return memory.ping(user.id)


@router.get("/memory/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Every number here is derived from logged Hindsight operations or stored records — nothing fabricated."""
    ev = db.query(MemoryEvent).filter(MemoryEvent.user_id == user.id)
    retains_ok = ev.filter(MemoryEvent.kind == "retain", MemoryEvent.success.is_(True)).count()
    recalls_ok = ev.filter(MemoryEvent.kind == "recall", MemoryEvent.success.is_(True)).count()
    failed = ev.filter(MemoryEvent.success.is_(False)).count()
    facts_recalled = (db.query(func.coalesce(func.sum(MemoryEvent.count), 0))
                      .filter(MemoryEvent.user_id == user.id, MemoryEvent.kind == "recall",
                              MemoryEvent.success.is_(True)).scalar())
    meetings = db.query(Meeting).filter(Meeting.user_id == user.id, Meeting.analysis_status == "confirmed").all()
    topics = Counter(i.topic for i in db.query(Insight).filter(Insight.user_id == user.id, Insight.kind == "discussion")
                     if i.topic)
    unresolved = [c for c in csvc.list_for_user(db, user.id, "all") if c.status in ("pending", "in_progress", "overdue")]

    summaries = []
    for c in db.query(Contact).filter(Contact.user_id == user.id).all():
        ms = [m for m in meetings if any(p.id == c.id for p in m.participants)]
        if not ms:
            continue
        open_n = sum(1 for x in unresolved if x.owner_contact_id == c.id)
        concern = (db.query(Insight).filter(Insight.user_id == user.id, Insight.kind == "concern",
                                            Insight.meeting_id.in_([m.id for m in ms]))
                   .order_by(Insight.id.desc()).first())
        summaries.append({"contact_id": c.id, "name": c.full_name, "organization": c.organization,
                          "meetings": len(ms), "open_commitments": open_n,
                          "last_interaction": max(m.scheduled_at for m in ms).isoformat(),
                          "latest_concern": concern.text if concern else None})

    recent = ev.order_by(MemoryEvent.created_at.desc(), MemoryEvent.id.desc()).limit(25).all()
    briefs = (db.query(Briefing).filter(Briefing.user_id == user.id).order_by(Briefing.created_at.desc()).limit(8).all())
    traces = []
    for b in briefs:
        c = json.loads(b.content)
        mem_refs = [{"ref": k, "text": v["text"], "source_meeting": v.get("source_meeting")}
                    for k, v in c.get("references", {}).items() if v["kind"] == "memory"]
        traces.append({"briefing_id": b.id, "meeting_id": b.meeting_id, "title": c["overview"]["title"],
                       "mode": b.mode, "created_at": b.created_at.isoformat(),
                       "memories_retrieved": b.memory_count, "memories": mem_refs})
    return {
        "meeting_interactions": len(meetings),
        "retain_operations": retains_ok,
        "recall_operations": recalls_ok,
        "facts_recalled_total": int(facts_recalled or 0),
        "failed_operations": failed,
        "unresolved_commitments": [u.model_dump(mode="json") for u in unresolved],
        "frequent_topics": [{"topic": t, "count": k} for t, k in topics.most_common(10)],
        "contact_summaries": summaries,
        "timeline": [{"id": e.id, "kind": e.kind, "success": e.success, "detail": e.detail, "count": e.count,
                      "meeting_id": e.meeting_id, "created_at": e.created_at.isoformat()} for e in recent],
        "briefing_traces": traces,
    }


@router.get("/settings/info")
def settings_info(user: User = Depends(current_user), llm: LLMClient = Depends(get_llm)):
    s = get_settings()
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name},
        "hindsight": {"url": s.hindsight_api_url, "api_key_configured": bool(s.hindsight_api_key),
                      "bank": f"{s.hindsight_bank_prefix}-user-{user.id}"},
        "llm": llm.describe(),
        "data_processing": (
            "Meeting notes you submit for analysis and the recalled memories used to prepare briefings are sent to the "
            f"LLM provider '{s.llm_provider}' (model {s.llm_model}). Confirmed facts are stored in Hindsight "
            "(your private memory bank). Nothing is shared across user accounts."),
    }
