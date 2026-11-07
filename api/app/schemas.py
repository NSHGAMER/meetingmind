from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- contacts ----------
class ContactIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    organization: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    relationship_notes: str | None = Field(default=None, max_length=4000)


class ContactOut(ContactIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_sample: bool = False
    created_at: datetime


# ---------- meetings ----------
MeetingStatus = Literal["scheduled", "completed", "cancelled"]


class MeetingIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    organization: str | None = Field(default=None, max_length=160)
    objective: str | None = Field(default=None, max_length=4000)
    agenda: str | None = Field(default=None, max_length=8000)
    scheduled_at: datetime
    status: MeetingStatus = "scheduled"
    notes: str | None = Field(default=None, max_length=60000)
    participant_ids: list[int] = []


class MeetingPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    organization: str | None = None
    objective: str | None = None
    agenda: str | None = None
    scheduled_at: datetime | None = None
    status: MeetingStatus | None = None
    notes: str | None = Field(default=None, max_length=60000)
    participant_ids: list[int] | None = None


class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    organization: str | None
    objective: str | None
    agenda: str | None
    scheduled_at: datetime
    status: str
    notes: str | None
    analysis_status: str
    is_sample: bool
    participants: list[ContactOut]


# ---------- extraction (LLM output, also edited by the user before confirmation) ----------
class ExtractedDiscussion(BaseModel):
    text: str
    topic: str | None = None


class ExtractedDecision(BaseModel):
    text: str
    status: Literal["approved", "rejected", "proposed"] = "approved"


class ExtractedCommitment(BaseModel):
    description: str
    owner_name: str
    due_date: date | None = None
    # "commitment" = explicitly promised; "suggestion" = proposed/maybe, NOT a confirmed commitment
    kind: Literal["commitment", "suggestion"] = "commitment"
    evidence: str | None = None


class ExtractedConcern(BaseModel):
    text: str
    raised_by: str | None = None


class ExtractedPreference(BaseModel):
    text: str
    person: str | None = None


class SuggestedStatusUpdate(BaseModel):
    """The notes hint that an EXISTING commitment changed. Never applied without user confirmation."""

    commitment_id: int
    suggested_status: Literal["pending", "in_progress", "completed", "cancelled"]
    evidence: str | None = None


class ExtractionResult(BaseModel):
    summary: str
    participants: list[str] = []
    topics: list[str] = []
    discussions: list[ExtractedDiscussion] = []
    decisions: list[ExtractedDecision] = []
    commitments: list[ExtractedCommitment] = []
    concerns: list[ExtractedConcern] = []
    preferences: list[ExtractedPreference] = []
    unresolved: list[str] = []
    follow_ups: list[str] = []
    suggested_status_updates: list[SuggestedStatusUpdate] = []


class AnalyzeOut(BaseModel):
    extraction: ExtractionResult
    processing_notice: str


class ConfirmIn(BaseModel):
    extraction: ExtractionResult
    accepted_status_update_ids: list[int] = []  # commitment ids whose suggested update the user accepts


# ---------- commitments ----------
CommitmentStatus = Literal["pending", "in_progress", "completed", "cancelled"]


class CommitmentOut(BaseModel):
    id: int
    description: str
    owner_name: str
    owner_contact_id: int | None
    meeting_id: int
    meeting_title: str
    meeting_date: datetime
    created_at: datetime
    due_date: date | None
    status: str  # effective status: includes "overdue"
    stored_status: str
    is_sample: bool


class CommitmentPatch(BaseModel):
    status: CommitmentStatus | None = None
    due_date: date | None = None
    description: str | None = None


class CommitmentPatchOut(BaseModel):
    commitment: CommitmentOut
    memory_synced: bool
    memory_error: str | None = None
