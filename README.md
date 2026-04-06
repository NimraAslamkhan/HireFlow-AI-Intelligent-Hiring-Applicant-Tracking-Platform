# 🎯 HireFlow — Full-Stack ATS (Applicant Tracking System)

A complete hiring management platform built with **FastAPI + SQLite + Vanilla JS**.

---

## 📁 Project Structure

```
hireflow/
├── backend/
│   ├── main.py               ← FastAPI app entry point
│   ├── .env                  ← Environment config
│   ├── models/
│   │   ├── database.py       ← SQLAlchemy engine & session
│   │   └── models.py         ← ORM models (User, Job, Candidate, etc.)
│   ├── schemas/
│   │   └── schemas.py        ← Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py           ← Login, register, profile
│   │   ├── users.py          ← Team management
│   │   ├── jobs.py           ← Job postings CRUD
│   │   ├── candidates.py     ← Candidates + resume upload/download
│   │   └── dashboard.py      ← Stats overview
│   ├── core/
│   │   ├── security.py       ← JWT auth + bcrypt passwords
│   │   └── files.py          ← Resume file handling
│   └── uploads/              ← Resume files stored here
│       └── <job_id>/<candidate_id>/<uuid>.pdf
├── frontend/
│   └── dashboard.html        ← Full-featured SPA dashboard
├── sample_candidates.csv     ← Test CSV for bulk import
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Setup (5 Minutes)

### 1. Install Python dependencies

```bash
cd hireflow
pip install -r requirements.txt
```

### 2. Start the server

```bash
uvicorn main:app --reload --port 8000
```

### 3. Open the dashboard

Open `frontend/dashboard.html` in your browser.

**Default login:**
- Email: `admin@hireflow.com`
- Password: `admin123`

---

## 🔗 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login → JWT token |
| GET | `/api/auth/me` | Get current user |
| PUT | `/api/auth/me` | Update profile |
| POST | `/api/auth/change-password` | Change password |

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all jobs |
| POST | `/api/jobs` | Create job |
| GET | `/api/jobs/{id}` | Get job |
| PUT | `/api/jobs/{id}` | Update job |
| DELETE | `/api/jobs/{id}` | Delete job |
| PATCH | `/api/jobs/{id}/status` | Change status |
| GET | `/api/jobs/{id}/stats` | Pipeline stats |

### Candidates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/candidates` | List/filter candidates |
| POST | `/api/candidates` | Create candidate |
| GET | `/api/candidates/{id}` | Get candidate |
| PUT | `/api/candidates/{id}` | Update candidate |
| DELETE | `/api/candidates/{id}` | Delete candidate |
| POST | `/api/candidates/{id}/resume` | Upload resume |
| GET | `/api/candidates/{id}/resume/download` | Download resume |
| DELETE | `/api/candidates/{id}/resume` | Remove resume |
| PATCH | `/api/candidates/{id}/stage` | Move pipeline stage |
| POST | `/api/candidates/{id}/star` | Toggle star |
| POST | `/api/candidates/{id}/archive` | Toggle archive |
| GET | `/api/candidates/{id}/comments` | List comments |
| POST | `/api/candidates/{id}/comments` | Add comment |
| DELETE | `/api/candidates/{id}/comments/{cid}` | Delete comment |
| GET | `/api/candidates/{id}/ratings` | List ratings |
| POST | `/api/candidates/{id}/ratings` | Rate candidate |
| GET | `/api/candidates/pipeline/{job_id}` | Kanban board |
| POST | `/api/candidates/import/csv` | Bulk CSV import |

### Dashboard & Users
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Stats overview |
| GET | `/api/users` | List users (admin) |
| PUT | `/api/users/{id}` | Update user role |
| DELETE | `/api/users/{id}` | Deactivate user |

### Interactive API Docs
Visit **http://localhost:8000/api/docs** for the full Swagger UI.

---

## ✨ Features

### Backend
- ✅ JWT Authentication with bcrypt password hashing
- ✅ Role-based access (admin / member / viewer)
- ✅ Complete job posting management
- ✅ Full candidate CRUD
- ✅ Resume upload (PDF, DOC, DOCX, TXT — max 10MB)
- ✅ Secure resume download via API
- ✅ Pipeline stage management (6 stages)
- ✅ Bulk CSV import with duplicate detection
- ✅ Team comments on candidates
- ✅ 1–5 star ratings per team member
- ✅ Star / Archive candidates
- ✅ Dashboard stats & pipeline breakdown
- ✅ SQLite database (zero config)

### Frontend Dashboard
- ✅ Login / Register screen
- ✅ Dashboard with stats, charts, recent candidates
- ✅ Jobs table with search/filter + create/edit/delete
- ✅ Candidates table with search/filter/sort
- ✅ Kanban pipeline board (visual drag-ready)
- ✅ Resume upload with drag & drop
- ✅ Resume download button
- ✅ Candidate detail modal with comments & ratings
- ✅ Pipeline stage changer (click to move)
- ✅ Team management page
- ✅ Profile & password change
- ✅ CSV import modal
- ✅ Toast notifications
- ✅ Responsive design

---

## 📊 CSV Import Format

```csv
full_name,email,phone,location,current_company,current_role,experience_years,notes,tags
Sarah Johnson,sarah@example.com,+1 555 100,New York,Google,Engineer,6,Notes here,python,react
```

**Required:** `full_name`, `email`  
**Optional:** `phone`, `location`, `current_company`, `current_role`, `experience_years`, `notes`, `tags`

---

## 🔒 Security Notes

Before going to production:
1. Change `SECRET_KEY` in `.env` to a random 64-character string
2. Change the default admin password
3. Set `CORS` origins to your actual domain
4. Use PostgreSQL instead of SQLite for production
5. Add HTTPS / reverse proxy (nginx)

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI |
| Database | SQLite (via SQLAlchemy ORM) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| File Storage | Local filesystem |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Fonts | Sora + DM Sans (Google Fonts) |
