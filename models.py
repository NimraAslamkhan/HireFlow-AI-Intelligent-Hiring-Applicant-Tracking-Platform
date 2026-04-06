"""
SQLAlchemy ORM Models for HireFlow
Tables: users, jobs, candidates, pipeline_stages, pipeline_entries, comments, ratings
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, Enum, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


# ── Enums ──────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin  = "admin"
    member = "member"
    viewer = "viewer"


class JobStatus(str, enum.Enum):
    draft     = "draft"
    active    = "active"
    paused    = "paused"
    closed    = "closed"


class PipelineStage(str, enum.Enum):
    applied      = "applied"
    screening    = "screening"
    interview    = "interview"
    offer        = "offer"
    hired        = "hired"
    rejected     = "rejected"


class CandidateSource(str, enum.Enum):
    csv_import   = "csv_import"
    google_forms = "google_forms"
    career_page  = "career_page"
    manual       = "manual"
    referral     = "referral"


# ── Models ─────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    email          = Column(String(255), unique=True, index=True, nullable=False)
    full_name      = Column(String(255), nullable=False)
    hashed_password= Column(String(255), nullable=False)
    role           = Column(Enum(UserRole), default=UserRole.member)
    avatar_url     = Column(String(500), nullable=True)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    jobs           = relationship("Job", back_populates="created_by_user")
    comments       = relationship("Comment", back_populates="author")
    ratings        = relationship("Rating", back_populates="rater")


class Job(Base):
    __tablename__ = "jobs"

    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String(255), nullable=False)
    department     = Column(String(100), nullable=True)
    location       = Column(String(200), nullable=True)
    job_type       = Column(String(50), default="Full-time")   # Full-time, Part-time, Contract
    description    = Column(Text, nullable=True)
    requirements   = Column(Text, nullable=True)
    salary_min     = Column(Integer, nullable=True)
    salary_max     = Column(Integer, nullable=True)
    status         = Column(Enum(JobStatus), default=JobStatus.active)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    created_by_user= relationship("User", back_populates="jobs")
    candidates     = relationship("Candidate", back_populates="job")

    @property
    def candidate_count(self):
        return len(self.candidates)


class Candidate(Base):
    __tablename__ = "candidates"

    id             = Column(Integer, primary_key=True, index=True)
    job_id         = Column(Integer, ForeignKey("jobs.id"), nullable=False)

    # Personal Info
    full_name      = Column(String(255), nullable=False)
    email          = Column(String(255), nullable=False, index=True)
    phone          = Column(String(50), nullable=True)
    location       = Column(String(200), nullable=True)
    linkedin_url   = Column(String(500), nullable=True)
    portfolio_url  = Column(String(500), nullable=True)

    # Resume
    resume_filename= Column(String(500), nullable=True)
    resume_path    = Column(String(500), nullable=True)
    resume_original= Column(String(500), nullable=True)   # original filename

    # Pipeline
    stage          = Column(Enum(PipelineStage), default=PipelineStage.applied)
    source         = Column(Enum(CandidateSource), default=CandidateSource.manual)

    # Extra
    cover_letter   = Column(Text, nullable=True)
    notes          = Column(Text, nullable=True)
    tags           = Column(String(500), nullable=True)   # comma-separated
    experience_years = Column(Integer, nullable=True)
    current_company  = Column(String(255), nullable=True)
    current_role     = Column(String(255), nullable=True)

    # Flags
    is_starred     = Column(Boolean, default=False)
    is_archived    = Column(Boolean, default=False)

    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    job            = relationship("Job", back_populates="candidates")
    comments       = relationship("Comment", back_populates="candidate", cascade="all, delete-orphan")
    ratings        = relationship("Rating", back_populates="candidate", cascade="all, delete-orphan")

    @property
    def avg_rating(self):
        if not self.ratings:
            return None
        return round(sum(r.score for r in self.ratings) / len(self.ratings), 1)


class Comment(Base):
    __tablename__ = "comments"

    id             = Column(Integer, primary_key=True, index=True)
    candidate_id   = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    author_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    content        = Column(Text, nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    candidate      = relationship("Candidate", back_populates="comments")
    author         = relationship("User", back_populates="comments")


class Rating(Base):
    __tablename__ = "ratings"

    id             = Column(Integer, primary_key=True, index=True)
    candidate_id   = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    rater_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    score          = Column(Float, nullable=False)   # 1.0 – 5.0
    category       = Column(String(100), default="overall")   # overall, technical, culture
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    candidate      = relationship("Candidate", back_populates="ratings")
    rater          = relationship("User", back_populates="ratings")
