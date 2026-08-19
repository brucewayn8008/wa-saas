from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.models.database import Workspace, WhatsAppSession, User
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/")
def read_workspaces(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # TODO Add schemas
    workspaces = db.query(Workspace).filter(Workspace.owner_id == current_user.id).offset(skip).limit(limit).all()
    return workspaces

@router.get("/{workspace_id}")
def read_workspace(workspace_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    ws = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.owner_id == current_user.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws

@router.get("/{workspace_id}/session")
def read_whatsapp_session(workspace_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # verify ownership first
    ws = db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.owner_id == current_user.id).first()
    if not ws:
         raise HTTPException(status_code=404, detail="Workspace not found")
         
    session = db.query(WhatsAppSession).filter(WhatsAppSession.workspace_id == workspace_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="WhatsApp config not found")
    return session
