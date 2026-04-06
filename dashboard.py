"""
Dashboard stats:
  GET /api/dashboard  — aggregated stats for the app
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime

from database import get_db
from models import Job, Candidate, User
from schemas import DashboardStats, CandidateOut
from security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()

    total_jobs  = db.query(func.count(Job.id)).scalar() or 0
    active_jobs = db.query(func.count(Job.id)).filter(Job.status == "active").scalar() or 0

    total_candidates = db.query(func.count(Candidate.id)).scalar() or 0

    hired_this_month = db.query(func.count(Candidate.id)).filter(
        Candidate.stage == "hired",
        extract("month", Candidate.updated_at) == now.month,
        extract("year",  Candidate.updated_at) == now.year,
    ).scalar() or 0

    # Pipeline breakdown (all jobs)
    stages = ["applied", "screening", "interview", "offer", "hired", "rejected"]
    pipeline_breakdown = {}
    for stage in stages:
        count = db.query(func.count(Candidate.id))\
            .filter(Candidate.stage == stage).scalar() or 0
        pipeline_breakdown[stage] = count

    # 5 most recent candidates
    recent = db.query(Candidate)\
        .order_by(Candidate.created_at.desc()).limit(5).all()

    return DashboardStats(
        total_jobs          = total_jobs,
        active_jobs         = active_jobs,
        total_candidates    = total_candidates,
        hired_this_month    = hired_this_month,
        pipeline_breakdown  = pipeline_breakdown,
        recent_candidates   = recent,
    )
