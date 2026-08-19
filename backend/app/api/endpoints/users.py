from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.session import get_db
from app.models.database import User
from app.core.auth import get_current_user

router = APIRouter()

class UpsertUserRequest(BaseModel):
    email: EmailStr

@router.get("/")
def read_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Keep scoped to the authenticated user for MVP safety.
    _ = current_user
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email, "created_at": u.created_at} for u in users]

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "created_at": current_user.created_at}

@router.post("/upsert")
def upsert_user(payload: UpsertUserRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        return {"id": user.id, "email": user.email, "created_at": user.created_at}

    user = User(email=payload.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "created_at": user.created_at}
