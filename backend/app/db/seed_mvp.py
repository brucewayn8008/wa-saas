import uuid
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal, engine
from app.models.database import Base, Lead, LeadStatus, Message, MessageRole, MessageStatus, User, Workspace


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@local.dev").first()
        if not user:
            user = User(email="demo@local.dev")
            db.add(user)
            db.commit()
            db.refresh(user)

        workspace = db.query(Workspace).filter(Workspace.owner_id == user.id).first()
        if not workspace:
            workspace = Workspace(
                id=uuid.uuid4(),
                owner_id=user.id,
                company_name="Demo Clinic",
                business_description="Clinic offering consultations and treatment plans.",
                whatsapp_jid="919999999999@s.whatsapp.net",
                system_prompt="You are a helpful sales assistant for our clinic.",
                agent_enabled=True,
            )
            db.add(workspace)
            db.commit()
            db.refresh(workspace)

        if db.query(Lead).filter(Lead.workspace_id == workspace.id).count() == 0:
            now = datetime.now(timezone.utc)
            samples = [
                ("Rahul Sharma", "919111111111@s.whatsapp.net", "HOT", 92, "needs_link"),
                ("Priya Verma", "919222222222@s.whatsapp.net", "WARM", 68, "in_conversation"),
                ("Amit Jain", "919333333333@s.whatsapp.net", "COLD", 31, "new"),
            ]
            for idx, (name, jid, intent, score, state_hint) in enumerate(samples):
                status = LeadStatus.NEW if state_hint == "new" else LeadStatus.IN_PROGRESS
                lead = Lead(
                    workspace_id=workspace.id,
                    jid=jid,
                    name=name,
                    status=status,
                    intent_label=intent,
                    score=score,
                    summary=f"{name} asked about pricing and availability.",
                    created_at=now - timedelta(hours=6 - idx),
                )
                db.add(lead)
                db.flush()
                db.add(
                    Message(
                        lead_id=lead.id,
                        workspace_id=workspace.id,
                        role=MessageRole.USER,
                        status=MessageStatus.RECEIVED,
                        content="Hi, can you share consultation details?",
                        timestamp=now - timedelta(hours=5 - idx),
                    )
                )
                db.add(
                    Message(
                        lead_id=lead.id,
                        workspace_id=workspace.id,
                        role=MessageRole.AGENT,
                        status=MessageStatus.DRAFT if intent == "HOT" else MessageStatus.SENT,
                        content="Thanks for reaching out. I can help you with available slots today.",
                        timestamp=now - timedelta(hours=4 - idx),
                    )
                )
            db.commit()

        print(f"Seed complete. workspace_id={workspace.id} user={user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
