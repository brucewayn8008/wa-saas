from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.models.database import Message, Lead, Workspace, User
from app.core.auth import get_current_user

router = APIRouter()

@router.get("/")
def read_messages(lead_id: UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verify the user owns the workspace that owns this lead
    lead = db.query(Lead).join(Workspace).filter(
        Lead.id == lead_id, 
        Workspace.owner_id == current_user.id
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    messages = db.query(Message).filter(Message.lead_id == lead_id).order_by(Message.timestamp.asc()).offset(skip).limit(limit).all()
    return messages

from pydantic import BaseModel
from typing import Optional
from app.models.database import MessageStatus
from app.tasks.whatsapp_tasks import send_whatsapp_message

class ApproveMessageRequest(BaseModel):
    content: Optional[str] = None

@router.patch("/{message_id}/approve")
def approve_message(message_id: UUID, req: ApproveMessageRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Verify ownership through the associated workspace
    message = db.query(Message).join(Lead).join(Workspace).filter(
        Message.id == message_id,
        Workspace.owner_id == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
        
    if message.status != MessageStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT messages can be approved.")
        
    if req.content:
        message.content = req.content
        
    message.status = MessageStatus.SENT
    db.commit()
    db.refresh(message)
    
    # Trigger Send Action
    lead = db.query(Lead).filter(Lead.id == message.lead_id).first()
    if lead:
        send_whatsapp_message.delay(
            workspace_id=str(message.workspace_id),
            to=lead.jid,
            text=message.content
        )
        
    return message
