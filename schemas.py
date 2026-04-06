"""
Pydantic v2 schemas — request bodies, response models, and shared types.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ── Enums (mirror DB enums) ────────────────────────────────────────────
class UserRole(str, Enum):
    admin  = "admin"
    member = "member"
    viewer = "viewer"


class JobStatus(str, Enum):
    draft   = "draft"
    active  = "active"
    paused  = "paused"
    closed  = "closed"


class PipelineStage(str, Enum):
    applied   = "applied"
    screening = "screening"
    interview = "interview"
    offer     = "offer"
    hired     = "hired"
    rejected  = "rejected"


class CandidateSource(str, Enum):
    csv_import   = "csv_import"
    google_forms = "google_forms"
    career_page  = "career_page"
    manual       = "manual"
    referral     = "referral"


# ── Auth ───────────────────────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ── User ───────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.member


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


# ── Job ────────────────────────────────────────────────────────────────
class JobCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: str = "Full-time"
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: JobStatus = JobStatus.active


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: Optional[JobStatus] = None


class JobOut(BaseModel):
    id: int
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: JobStatus
    created_by: int
    candidate_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Candidate ──────────────────────────────────────────────────────────
class CandidateCreate(BaseModel):
    job_id: int
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    stage: PipelineStage = PipelineStage.applied
    source: CandidateSource = CandidateSource.manual
    cover_letter: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    experience_years: Optional[int] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None


class CandidateUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    stage: Optional[PipelineStage] = None
    cover_letter: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    experience_years: Optional[int] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    is_starred: Optional[bool] = None
    is_archived: Optional[bool] = None


class CandidateOut(BaseModel):
    id: int
    job_id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    resume_filename: Optional[str] = None
    resume_original: Optional[str] = None
    stage: PipelineStage
    source: CandidateSource
    cover_letter: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    experience_years: Optional[int] = None
    current_company: Optional[str] = None
    current_role: Optional[str] = None
    is_starred: bool
    is_archived: bool
    avg_rating: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StageMove(BaseModel):
    stage: PipelineStage


# ── Pipeline ───────────────────────────────────────────────────────────
class PipelineColumn(BaseModel):
    stage: PipelineStage
    label: str
    count: int
    candidates: List[CandidateOut]


class PipelineBoard(BaseModel):
    job_id: int
    job_title: str
    columns: List[PipelineColumn]


# ── Comment ────────────────────────────────────────────────────────────
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: int
    candidate_id: int
    author_id: int
    content: str
    author: UserOut
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Rating ─────────────────────────────────────────────────────────────
class RatingCreate(BaseModel):
    score: float = Field(..., ge=1.0, le=5.0)
    category: str = "overall"


class RatingOut(BaseModel):
    id: int
    candidate_id: int
    rater_id: int
    score: float
    category: str
    rater: UserOut
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ──────────────────────────────────────────────────────────
class DashboardStats(BaseModel):
    total_jobs: int
    active_jobs: int
    total_candidates: int
    hired_this_month: int
    pipeline_breakdown: dict
    recent_candidates: List[CandidateOut]


# Forward ref update
Token.model_rebuild()
