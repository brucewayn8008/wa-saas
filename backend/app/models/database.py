import enum
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# pgvector is an optional runtime dep for the memory/intent features (Feature 13).
# Guard the import so models still load if it isn't installed yet; the Alembic
# migration creates the real `vector(768)` column via raw SQL regardless.
try:  # pragma: no cover
    from pgvector.sqlalchemy import Vector as _Vector

    def _embedding_column():
        return mapped_column(_Vector(768), nullable=True)
except ImportError:  # pragma: no cover
    def _embedding_column():
        return mapped_column(Text, nullable=True)

class Base(DeclarativeBase):
    pass

# Semantic alias: in this SaaS a Workspace IS the tenant (one per Clerk Organization).
# New code should refer to `Tenant`; the DB table remains `workspaces` for now.
# (Defined at the bottom of this module once Workspace exists.)

class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    CONVERTED = "CONVERTED"
    FAILED = "FAILED"

class MessageRole(str, enum.Enum):
    USER = "user"      # inbound from the contact
    AGENT = "agent"    # outbound from the AI agent
    HUMAN = "human"    # outbound from a human operator (manual reply during takeover)

class MessageStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    RECEIVED = "received"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspaces: Mapped[List["Workspace"]] = relationship("Workspace", back_populates="owner", cascade="all, delete-orphan")

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_description: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_jid: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True) # Made nullable as it might wait for QR scan
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # --- SaaS multi-tenancy (Feature 02) ---
    clerk_org_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=True)  # tenant key: "user:{sub}" (free plan) or Clerk org_id (paid plan)
    disclosure_line: Mapped[str] = mapped_column(Text, nullable=True, default="You're chatting with an AI assistant.")  # mandatory AI disclosure
    default_provider: Mapped[str] = mapped_column(String(30), default="wacli", nullable=False)  # wacli | whatsmeow | cloud_api

    owner: Mapped["User"] = relationship("User", back_populates="workspaces")

    # Agent Settings
    system_prompt: Mapped[str] = mapped_column(Text, nullable=True, default="You are a helpful AI assistant.")
    agent_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    is_running: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    daily_message_limit: Mapped[int] = mapped_column(Integer, default=35, nullable=False)
    messages_sent_today: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_daily_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    leads: Mapped[List["Lead"]] = relationship("Lead", back_populates="workspace", cascade="all, delete-orphan")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="workspace", cascade="all, delete-orphan")
    target_groups: Mapped[List["TargetGroup"]] = relationship("TargetGroup", back_populates="workspace", cascade="all, delete-orphan")
    whatsapp_session: Mapped["WhatsAppSession"] = relationship("WhatsAppSession", back_populates="workspace", uselist=False, cascade="all, delete-orphan")
    activities: Mapped[List["AgentActivity"]] = relationship("AgentActivity", back_populates="workspace", cascade="all, delete-orphan")
    
class WhatsAppSession(Base):
    __tablename__ = "whatsapp_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="UNCONFIGURED", nullable=False)
    qr_code: Mapped[str] = mapped_column(Text, nullable=True) # latest QR code
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="whatsapp_session")

class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    jid: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    intent_label: Mapped[str] = mapped_column(String(50), nullable=True)
    score: Mapped[int] = mapped_column(nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_contacted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    source: Mapped[str] = mapped_column(String(50), default="DIRECT", nullable=False)
    source_group_jid: Mapped[str] = mapped_column(String(255), nullable=True)
    source_group_name: Mapped[str] = mapped_column(String(255), nullable=True)
    service_interest: Mapped[str] = mapped_column(String(255), nullable=True)
    requirement_summary: Mapped[str] = mapped_column(Text, nullable=True)
    meeting_status: Mapped[str] = mapped_column(String(50), default="NOT_REQUESTED", nullable=False)
    meeting_notes: Mapped[str] = mapped_column(Text, nullable=True)
    next_action: Mapped[str] = mapped_column(Text, nullable=True)
    last_inbound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_outbound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_response: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="leads")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="lead", cascade="all, delete-orphan")
    assigned_to: Mapped["User"] = relationship("User")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    status: Mapped[MessageStatus] = mapped_column(Enum(MessageStatus), default=MessageStatus.SENT, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    wa_message_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    # Tenant brand asset (outbound) or received prospect media (inbound) — never a foreign tenant's.
    media_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    lead: Mapped["Lead"] = relationship("Lead", back_populates="messages")
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="messages")

class TargetGroup(Base):
    __tablename__ = "target_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    jid: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    custom_offer: Mapped[str] = mapped_column(Text, nullable=True)
    last_promo_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="target_groups")

class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    group_jid: Mapped[str] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="activities")

# =========================================================================
# SaaS multi-tenant tables (Feature 02). All are tenant-scoped via
# workspace_id (the tenant boundary) and protected by RLS — see the Alembic
# migration. New code should treat `workspace_id` as the tenant id.
# =========================================================================

class TenantMember(Base):
    """A Clerk user's membership + role in a tenant (workspace)."""
    __tablename__ = "tenant_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    clerk_user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(30), default="agent", nullable=False)  # owner | admin | agent

class WANumber(Base):
    """A connected WhatsApp number for a tenant. Replaces the single WhatsAppSession."""
    __tablename__ = "wa_numbers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), default="wacli", nullable=False)  # wacli | whatsmeow | cloud_api
    # Cloud API (deferred)
    phone_number_id: Mapped[str] = mapped_column(String(64), index=True, nullable=True)
    waba_id: Mapped[str] = mapped_column(String(64), nullable=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=True)  # store encrypted / via secret ref in prod
    messaging_tier: Mapped[int] = mapped_column(Integer, nullable=True)
    # wacli / whatsmeow
    jid: Mapped[str] = mapped_column(String(255), nullable=True)
    qr_code: Mapped[str] = mapped_column(Text, nullable=True)
    wacli_store_dir: Mapped[str] = mapped_column(Text, nullable=True)  # --store path for this number
    wacli_account: Mapped[str] = mapped_column(String(128), nullable=True)  # optional named subdir under store base
    status: Mapped[str] = mapped_column(String(50), default="UNCONFIGURED", nullable=False)

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    wa_number_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wa_numbers.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)  # active | paused | ended
    human_takeover: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_inbound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)  # drives 24h window
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MemoryFact(Base):
    """Facts the lead stated (service, budget, timeline), with an embedding for recall."""
    __tablename__ = "memory_facts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=True)  # service | budget | timeline | preference
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = _embedding_column()
    confidence: Mapped[int] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="stated", nullable=False)  # stated | inferred
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MediaAsset(Base):
    """A tenant's own approved brand media. Binary lives in object storage; only the key is here."""
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="image", nullable=False)  # image | video
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    wa_media_id: Mapped[str] = mapped_column(String(128), nullable=True)  # cached Cloud API media id
    mime: Mapped[str] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    wa_template_name: Mapped[str] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Consent(Base):
    """Proof-of-relationship for a lead — the basis outreach_policy requires."""
    __tablename__ = "consent"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # inbound | widget | ad | import
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), unique=True, nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(64), nullable=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(64), nullable=True)
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="inactive", nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    # quota columns
    max_numbers: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    monthly_conversation_quota: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_seats: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    media_storage_mb: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

class Usage(Base):
    __tablename__ = "usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    conversations_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    media_stored_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ListeningLead(Base):
    """Group-intent detection audit row — auto-replied when the gate allows (Feature 16).

    Listening never scrapes members; it only reacts to public messages in groups the
    tenant already belongs to. Soft-dismiss hides the card from /listening.
    """

    __tablename__ = "listening_leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    group_jid: Mapped[str] = mapped_column(String(255), nullable=False)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_jid: Mapped[str] = mapped_column(String(255), nullable=False)
    original_message: Mapped[str] = mapped_column(Text, nullable=False)
    match_reason: Mapped[str] = mapped_column(String(30), nullable=False)  # keyword | semantic
    match_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0–100 when semantic
    reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # detected → reply pending; sent → auto-dispatched; blocked → gate denied; dismissed → hidden
    status: Mapped[str] = mapped_column(String(30), default="detected", nullable=False)
    block_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Semantic alias — use `Tenant` in new code. Same table/rows as Workspace.
Tenant = Workspace
