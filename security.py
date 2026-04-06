"""
Security: password hashing with bcrypt, JWT token creation/verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import User
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY   = os.getenv("SECRET_KEY", "changeme")
ALGORITHM    = os.getenv("ALGORITHM", "HS256")
EXPIRE_MINS  = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 10080))

pwd_context  = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Passwords ──────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ────────────────────────────────────────────────────────────────
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=EXPIRE_MINS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[int]:
    """Returns user_id from token, or None if invalid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[int] = payload.get("sub")
        return int(user_id) if user_id else None
    except JWTError:
        return None


# ── FastAPI Dependencies ───────────────────────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Dependency that returns the authenticated User ORM object.
    Import and use inside router dependencies.
    """


    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_token(token)
    if not user_id:
        raise credentials_exc

    # db is injected by FastAPI when used as Depends
    if db is None:
        raise credentials_exc


    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exc
    return user


def require_admin(current_user=Depends(get_current_user)):
    from models import UserRole
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
