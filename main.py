"""
HireFlow — FastAPI Application Entry Point
Run with: uvicorn main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Import models & create tables ──────────────────────────────────────
from database import engine, Base, get_db
import models  # registers all ORM models
Base.metadata.create_all(bind=engine)

# ── Import routers ─────────────────────────────────────────────────────
from auth       import router as auth_router
from users      import router as users_router
from jobs       import router as jobs_router
from candidates import router as candidates_router
from dashboard  import router as dashboard_router


# ── Lifespan event handler ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from database import SessionLocal
    from models import User, UserRole
    from security import hash_password

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.email == "admin@hireflow.com").first():
            admin = User(
                email           = "admin@hireflow.com",
                full_name       = "Admin User",
                hashed_password = hash_password("admin123"),
                role            = UserRole.admin,
            )
            db.add(admin)
            db.commit()
            print("\n✅  Default admin created:")
            print("    Email:    admin@hireflow.com")
            print("    Password: admin123")
            print("    ⚠️  Change this password immediately!\n")
    finally:
        db.close()
    
    yield
    
    # Shutdown (if needed)
    pass




# ── App factory ────────────────────────────────────────────────────────
app = FastAPI(
    title       = "HireFlow API",
    description = "Applicant Tracking System — candidates, jobs, pipeline, resume uploads",
    version     = "1.0.0",
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
    lifespan    = lifespan,
)

# CORS — allow the React/HTML frontend on localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["http://localhost:3000", "http://localhost:5500",
                      "http://127.0.0.1:5500", "http://localhost:8080",
                      "*"],   # tighten in production
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

# ── Ensure upload directory exists ────────────────────────────────────
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
Path(UPLOAD_DIR).mkdir(exist_ok=True)

# ── Static files (uploaded resumes) ───────────────────────────────────
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ── Mount frontend static files ───────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# ── Register API Routers ───────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(dashboard_router)


# ── Health check ──────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
def health():
    return {"status": "ok", "app": "HireFlow", "version": "1.0.0"}


# ── Serve frontend index for any unmatched route ──────────────────────
@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"detail": "Frontend not found. Place index.html in frontend/"}, 404)
