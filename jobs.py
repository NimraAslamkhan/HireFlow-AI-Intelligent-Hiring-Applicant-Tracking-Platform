"""
Job Postings CRUD:
  GET    /api/jobs              — list all jobs (with candidate counts)
  POST   /api/jobs              — create job
  GET    /api/jobs/{id}         — get single job
  PUT    /api/jobs/{id}         — update job
  DELETE /api/jobs/{id}         — delete job
  PATCH  /api/jobs/{id}/status  — change status (active/paused/closed)
  GET    /api/jobs/{id}/stats   — pipeline stats for a job
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from database import get_db
from models import Job, Candidate, PipelineStage
from schemas import JobCreate, JobUpdate, JobOut
from security import get_current_user
from models import User

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("", response_model=List[JobOut])
def list_jobs(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List jobs with optional status filter and search."""
    q = db.query(Job)
    if status:
        q = q.filter(Job.status == status)
    if search:
        q = q.filter(Job.title.ilike(f"%{search}%"))
    jobs = q.order_by(Job.created_at.desc()).all()

    # Attach candidate counts
    for job in jobs:
        job.__dict__["candidate_count"] = db.query(func.count(Candidate.id))\
            .filter(Candidate.job_id == job.id).scalar() or 0
    return jobs


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = Job(**payload.model_dump(), created_by=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    job.__dict__["candidate_count"] = 0
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.__dict__["candidate_count"] = db.query(func.count(Candidate.id))\
        .filter(Candidate.job_id == job_id).scalar() or 0
    return job


@router.put("/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    job.__dict__["candidate_count"] = db.query(func.count(Candidate.id))\
        .filter(Candidate.job_id == job_id).scalar() or 0
    return job


@router.delete("/{job_id}", status_code=200)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"message": "Job deleted"}


@router.patch("/{job_id}/status", response_model=JobOut)
def change_job_status(
    job_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = status
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}/stats")
def job_pipeline_stats(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns count breakdown by pipeline stage for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stages = ["applied", "screening", "interview", "offer", "hired", "rejected"]
    breakdown = {}
    for stage in stages:
        count = db.query(func.count(Candidate.id))\
            .filter(Candidate.job_id == job_id, Candidate.stage == stage).scalar() or 0
        breakdown[stage] = count

    total = sum(breakdown.values())
    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_candidates": total,
        "pipeline": breakdown,
    }
