"""
Candidates — full CRUD + resume upload/download + pipeline management:

  GET    /api/candidates                      — list / filter
  POST   /api/candidates                      — create candidate (JSON)
  GET    /api/candidates/{id}                 — get single candidate
  PUT    /api/candidates/{id}                 — update candidate
  DELETE /api/candidates/{id}                 — delete candidate
  POST   /api/candidates/{id}/resume          — upload resume
  GET    /api/candidates/{id}/resume/download — download resume file
  DELETE /api/candidates/{id}/resume          — remove resume
  PATCH  /api/candidates/{id}/stage           — move pipeline stage
  POST   /api/candidates/{id}/star            — toggle star
  POST   /api/candidates/{id}/archive         — toggle archive
  GET    /api/candidates/{id}/comments        — list comments
  POST   /api/candidates/{id}/comments        — add comment
  DELETE /api/candidates/{id}/comments/{cid} — delete comment
  GET    /api/candidates/{id}/ratings         — list ratings
  POST   /api/candidates/{id}/ratings         — submit rating

  POST   /api/candidates/import/csv           — bulk import from CSV text
"""

import csv, io
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File,
    Query, BackgroundTasks
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from database import get_db
from models import Candidate, Comment, Rating, Job, User
from schemas import (
    CandidateCreate, CandidateUpdate, CandidateOut, StageMove,
    CommentCreate, CommentOut, RatingCreate, RatingOut,
    PipelineBoard, PipelineColumn, PipelineStage,
)
from security import get_current_user
from files import save_resume, delete_resume, resume_exists

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])


# ── helpers ────────────────────────────────────────────────────────────
def _get_candidate_or_404(candidate_id: int, db: Session) -> Candidate:
    c = db.query(Candidate)\
        .options(joinedload(Candidate.ratings), joinedload(Candidate.comments))\
        .filter(Candidate.id == candidate_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return c


# ── List / Filter ──────────────────────────────────────────────────────
@router.get("", response_model=List[CandidateOut])
def list_candidates(
    job_id:   Optional[int]  = Query(None),
    stage:    Optional[str]  = Query(None),
    search:   Optional[str]  = Query(None),
    starred:  Optional[bool] = Query(None),
    archived: Optional[bool] = Query(False),
    skip:     int            = Query(0, ge=0),
    limit:    int            = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Candidate)\
        .options(joinedload(Candidate.ratings), joinedload(Candidate.comments))

    if job_id   is not None: q = q.filter(Candidate.job_id == job_id)
    if stage    is not None: q = q.filter(Candidate.stage  == stage)
    if starred  is not None: q = q.filter(Candidate.is_starred  == starred)
    if archived is not None: q = q.filter(Candidate.is_archived == archived)
    if search:
        term = f"%{search}%"
        q = q.filter(
            Candidate.full_name.ilike(term) |
            Candidate.email.ilike(term) |
            Candidate.current_company.ilike(term)
        )

    return q.order_by(Candidate.created_at.desc()).offset(skip).limit(limit).all()


# ── Create ─────────────────────────────────────────────────────────────
@router.post("", response_model=CandidateOut, status_code=201)
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not db.query(Job).filter(Job.id == payload.job_id).first():
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = Candidate(**payload.model_dump())
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return _get_candidate_or_404(candidate.id, db)


# ── Get one ────────────────────────────────────────────────────────────
@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_candidate_or_404(candidate_id, db)


# ── Update ─────────────────────────────────────────────────────────────
@router.put("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(candidate_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(candidate, field, value)
    db.commit()
    return _get_candidate_or_404(candidate_id, db)


# ── Delete ─────────────────────────────────────────────────────────────
@router.delete("/{candidate_id}", status_code=200)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(candidate_id, db)
    delete_resume(candidate.resume_path)
    db.delete(candidate)
    db.commit()
    return {"message": "Candidate deleted"}


# ── Resume Upload ──────────────────────────────────────────────────────
@router.post("/{candidate_id}/resume", response_model=CandidateOut)
async def upload_resume(
    candidate_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload / replace a candidate's resume (PDF, DOC, DOCX, TXT — max 10 MB)."""
    candidate = _get_candidate_or_404(candidate_id, db)

    # Remove old file if any
    delete_resume(candidate.resume_path)

    result = await save_resume(file, candidate.job_id, candidate_id)

    candidate.resume_filename = result["filename"]
    candidate.resume_path     = result["path"]
    candidate.resume_original = result["original"]
    db.commit()

    return _get_candidate_or_404(candidate_id, db)


# ── Resume Download ────────────────────────────────────────────────────
@router.get("/{candidate_id}/resume/download")
def download_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream resume file to client as a download."""
    candidate = _get_candidate_or_404(candidate_id, db)

    if not candidate.resume_path or not resume_exists(candidate.resume_path):
        raise HTTPException(status_code=404, detail="No resume on file")

    return FileResponse(
        path        = candidate.resume_path,
        filename    = candidate.resume_original or candidate.resume_filename,
        media_type  = "application/octet-stream",
    )


# ── Resume Delete ──────────────────────────────────────────────────────
@router.delete("/{candidate_id}/resume", status_code=200)
def remove_resume(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(candidate_id, db)
    delete_resume(candidate.resume_path)
    candidate.resume_filename = None
    candidate.resume_path     = None
    candidate.resume_original = None
    db.commit()
    return {"message": "Resume removed"}


# ── Pipeline Stage ─────────────────────────────────────────────────────
@router.patch("/{candidate_id}/stage", response_model=CandidateOut)
def move_stage(
    candidate_id: int,
    payload: StageMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(candidate_id, db)
    candidate.stage = payload.stage
    db.commit()
    return _get_candidate_or_404(candidate_id, db)


# ── Star / Archive Toggles ─────────────────────────────────────────────
@router.post("/{candidate_id}/star", response_model=CandidateOut)
def toggle_star(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(candidate_id, db)
    candidate.is_starred = not candidate.is_starred
    db.commit()
    return _get_candidate_or_404(candidate_id, db)


@router.post("/{candidate_id}/archive", response_model=CandidateOut)
def toggle_archive(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = _get_candidate_or_404(candidate_id, db)
    candidate.is_archived = not candidate.is_archived
    db.commit()
    return _get_candidate_or_404(candidate_id, db)


# ── Comments ───────────────────────────────────────────────────────────
@router.get("/{candidate_id}/comments", response_model=List[CommentOut])
def list_comments(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(candidate_id, db)
    return db.query(Comment)\
        .options(joinedload(Comment.author))\
        .filter(Comment.candidate_id == candidate_id)\
        .order_by(Comment.created_at.asc()).all()


@router.post("/{candidate_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    candidate_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(candidate_id, db)
    comment = Comment(
        candidate_id = candidate_id,
        author_id    = current_user.id,
        content      = payload.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return db.query(Comment).options(joinedload(Comment.author)).filter(Comment.id == comment.id).first()


@router.delete("/{candidate_id}/comments/{comment_id}", status_code=200)
def delete_comment(
    candidate_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(Comment).filter(
        Comment.id == comment_id, Comment.candidate_id == candidate_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}


# ── Ratings ────────────────────────────────────────────────────────────
@router.get("/{candidate_id}/ratings", response_model=List[RatingOut])
def list_ratings(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(candidate_id, db)
    return db.query(Rating)\
        .options(joinedload(Rating.rater))\
        .filter(Rating.candidate_id == candidate_id).all()


@router.post("/{candidate_id}/ratings", response_model=RatingOut, status_code=201)
def rate_candidate(
    candidate_id: int,
    payload: RatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_candidate_or_404(candidate_id, db)
    # Upsert: one rating per rater per category per candidate
    existing = db.query(Rating).filter(
        Rating.candidate_id == candidate_id,
        Rating.rater_id     == current_user.id,
        Rating.category     == payload.category,
    ).first()

    if existing:
        existing.score = payload.score
        db.commit()
        rating = existing
    else:
        rating = Rating(
            candidate_id = candidate_id,
            rater_id     = current_user.id,
            score        = payload.score,
            category     = payload.category,
        )
        db.add(rating)
        db.commit()
        db.refresh(rating)

    return db.query(Rating).options(joinedload(Rating.rater)).filter(Rating.id == rating.id).first()


# ── Kanban Pipeline Board ──────────────────────────────────────────────
@router.get("/pipeline/{job_id}", response_model=PipelineBoard)
def get_pipeline_board(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the full kanban board for a job, grouped by pipeline stage."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    stage_labels = {
        "applied":   "Applied",
        "screening": "Screening",
        "interview": "Interview",
        "offer":     "Offer",
        "hired":     "Hired",
        "rejected":  "Rejected",
    }

    columns = []
    for stage_key, label in stage_labels.items():
        candidates = db.query(Candidate)\
            .options(joinedload(Candidate.ratings))\
            .filter(
                Candidate.job_id    == job_id,
                Candidate.stage     == stage_key,
                Candidate.is_archived == False,
            ).order_by(Candidate.created_at.desc()).all()

        columns.append(PipelineColumn(
            stage      = stage_key,
            label      = label,
            count      = len(candidates),
            candidates = candidates,
        ))

    return PipelineBoard(job_id=job_id, job_title=job.title, columns=columns)


# ── CSV Import ─────────────────────────────────────────────────────────
@router.post("/import/csv", status_code=201)
async def import_csv(
    job_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk import candidates from a CSV file.
    Required columns: full_name, email
    Optional: phone, location, current_company, current_role, experience_years, notes, tags
    """
    if not db.query(Job).filter(Job.id == job_id).first():
        raise HTTPException(status_code=404, detail="Job not found")

    content = await file.read()
    decoded = content.decode("utf-8-sig")    # handle BOM
    reader  = csv.DictReader(io.StringIO(decoded))

    required = {"full_name", "email"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must have columns: {', '.join(required)}. Found: {reader.fieldnames}",
        )

    created, skipped, errors = [], [], []

    for i, row in enumerate(reader, start=2):   # row 1 = header
        name  = (row.get("full_name") or "").strip()
        email = (row.get("email") or "").strip()

        if not name or not email:
            skipped.append({"row": i, "reason": "Missing name or email"})
            continue

        # Skip duplicate emails for this job
        if db.query(Candidate).filter(
            Candidate.job_id == job_id, Candidate.email == email
        ).first():
            skipped.append({"row": i, "reason": f"Duplicate email: {email}"})
            continue

        try:
            exp = row.get("experience_years", "").strip()
            candidate = Candidate(
                job_id           = job_id,
                full_name        = name,
                email            = email,
                phone            = row.get("phone", "").strip() or None,
                location         = row.get("location", "").strip() or None,
                current_company  = row.get("current_company", "").strip() or None,
                current_role     = row.get("current_role", "").strip() or None,
                experience_years = int(exp) if exp.isdigit() else None,
                notes            = row.get("notes", "").strip() or None,
                tags             = row.get("tags", "").strip() or None,
                source           = "csv_import",
            )
            db.add(candidate)
            created.append(email)
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    db.commit()

    return {
        "imported": len(created),
        "skipped":  len(skipped),
        "errors":   len(errors),
        "details":  {"skipped": skipped, "errors": errors},
    }
