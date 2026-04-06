"""
Resume / file upload helpers.
Saves files to  backend/uploads/<job_id>/<candidate_id>/  with a UUID prefix.
"""

import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR      = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_MB     = int(os.getenv("MAX_FILE_SIZE_MB", 10))
MAX_BYTES       = MAX_FILE_MB * 1024 * 1024

ALLOWED_TYPES   = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
ALLOWED_EXT     = {".pdf", ".doc", ".docx", ".txt"}


def _ensure_dir(path: str):
    Path(path).mkdir(parents=True, exist_ok=True)


def get_upload_path(job_id: int, candidate_id: int) -> str:
    folder = os.path.join(UPLOAD_DIR, str(job_id), str(candidate_id))
    _ensure_dir(folder)
    return folder


async def save_resume(
    file: UploadFile,
    job_id: int,
    candidate_id: int,
) -> dict:
    """
    Validate & save an uploaded resume.
    Returns  {"filename": "<uuid>.pdf", "path": "uploads/1/3/<uuid>.pdf",
              "original": "resume.pdf"}
    """

    # ── Validate extension ──────────────────────────────────────────
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Use: {', '.join(ALLOWED_EXT)}",
        )

    # ── Read & check size ───────────────────────────────────────────
    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {MAX_FILE_MB} MB.",
        )

    # ── Save ────────────────────────────────────────────────────────
    unique_name = f"{uuid.uuid4().hex}{ext}"
    folder      = get_upload_path(job_id, candidate_id)
    save_path   = os.path.join(folder, unique_name)

    async with aiofiles.open(save_path, "wb") as f:
        await f.write(contents)

    return {
        "filename": unique_name,
        "path":     save_path,
        "original": file.filename,
    }


def delete_resume(path: str):
    """Remove a resume file from disk silently."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def resume_exists(path: str) -> bool:
    return bool(path and os.path.exists(path))
