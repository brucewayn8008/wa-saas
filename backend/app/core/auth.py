"""Clerk authentication + user->tenant resolution (Feature 09 / A1).

Security model:
  * Session JWTs are verified against Clerk's JWKS (RS256). No unverified decode.
  * The Clerk user `sub` is read from the VERIFIED token and is the tenant key.
  * Tenant model: one Workspace per Clerk user (free-plan, no Organizations).
    The `clerk_org_id` column stores `user:{sub}` as the lookup key.
  * If a Clerk Organization claim is present in future (paid plan), the org path
    is preserved and takes priority — no code change needed to upgrade.
  * A dev fallback exists ONLY when ENV != prod and Clerk is unconfigured.

Bootstrapping note: tenant resolution runs on a plain session because `workspaces`/
`tenant_members` are intentionally not RLS-scoped (see the a1b2c3d4e5f6 migration).
Tenant-scoped DATA access uses `get_tenant_db`, which opens an RLS session via
`tenant_context`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenancy import tenant_context
from app.db.session import SessionLocal
from app.models.database import TenantMember, User, Workspace

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

# Cache one JWKS client per URL (each holds its own key cache).
_jwks_clients: dict[str, "jwt.PyJWKClient"] = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Pure helpers (unit-testable without network/DB)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class OrgClaims:
    org_id: Optional[str]
    role: Optional[str]
    slug: Optional[str]


def extract_org(claims: dict) -> OrgClaims:
    """Read org context from a Clerk session token, supporting both the v2 `o`
    object claim and the legacy flat `org_*` claims."""
    o = claims.get("o")
    if isinstance(o, dict):
        return OrgClaims(org_id=o.get("id"), role=_normalize_role(o.get("rol")), slug=o.get("slg"))
    return OrgClaims(
        org_id=claims.get("org_id"),
        role=_normalize_role(claims.get("org_role")),
        slug=claims.get("org_slug"),
    )


def _normalize_role(role: Optional[str]) -> Optional[str]:
    """Clerk emits roles as `org:admin`; the v2 `rol` claim may drop the prefix
    (`admin`). Normalize to the bare role name used by `require_role`."""
    if not role:
        return None
    return role.split(":", 1)[1] if role.startswith("org:") else role


def _jwks_url_from(claims: dict) -> Optional[str]:
    if settings.CLERK_JWKS_URL:
        return settings.CLERK_JWKS_URL
    iss = claims.get("iss")
    return f"{iss.rstrip('/')}/.well-known/jwks.json" if iss else None


# --------------------------------------------------------------------------- #
# Token verification
# --------------------------------------------------------------------------- #

def _verify_signature(token: str) -> dict:
    # Peek (unverified) only to discover the issuer -> JWKS URL. The result is
    # discarded; the authoritative decode below verifies the signature.
    try:
        unverified = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Malformed token") from e

    jwks_url = _jwks_url_from(unverified)
    if not jwks_url:
        raise HTTPException(status_code=401, detail="No JWKS URL configured")

    client = _jwks_clients.get(jwks_url)
    if client is None:
        client = jwt.PyJWKClient(jwks_url)
        _jwks_clients[jwks_url] = client

    try:
        signing_key = client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk session tokens have no aud by default
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError as e:
        logger.warning("[auth] JWT verification failed: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_clerk_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    clerk_configured = bool(settings.CLERK_SECRET_KEY or settings.CLERK_JWKS_URL)

    # Dev fallback — only when NOT production and Clerk is unconfigured.
    if not clerk_configured:
        if settings.IS_PROD:
            raise HTTPException(status_code=500, detail="Auth not configured")
        email = request.headers.get("x-user-email", "demo@local.dev")
        sub = request.headers.get("x-user-id", "user_dev")
        logger.info("[auth] DEV fallback user=%s sub=%s", email, sub)
        # No org claims — uses the user→tenant path (matches free-plan prod behaviour).
        return {"sub": sub, "email": email, "iss": "dev"}

    if not credentials or not credentials.credentials or credentials.credentials == "null":
        raise HTTPException(status_code=401, detail="Missing authorization token")

    return _verify_signature(credentials.credentials)


# --------------------------------------------------------------------------- #
# Provisioning + context
# --------------------------------------------------------------------------- #

@dataclass
class AuthContext:
    user: User
    tenant: Workspace          # a Workspace IS the tenant
    clerk_user_id: str         # Clerk `sub` — the identity anchor
    role: str                  # "admin" for solo users; "member" / custom if orgs enabled later

    @property
    def tenant_id(self) -> str:
        return str(self.tenant.id)


def _resolve_email(claims: dict) -> str:
    return (
        claims.get("email")
        or claims.get("primary_email_address")
        or f"{claims.get('sub', 'unknown')}@clerk.user"
    )


def provision(db: Session, claims: dict) -> AuthContext:
    """Idempotently ensure the user and their tenant workspace exist.

    Free-plan path (default): tenant key = `user:{sub}`. One workspace per user.
    Paid-plan / org path (future): if the token carries org claims the org id is
    used as the tenant key instead — no code change needed when upgrading.
    """
    email = _resolve_email(claims)
    sub = claims.get("sub", "")
    org = extract_org(claims)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email)
        db.add(user)
        db.flush()

    # Tenant resolution — org takes priority when present (future paid plan).
    if org.org_id:
        tenant_key = org.org_id
        role = org.role or "member"
        display_name = org.slug or "My Workspace"
    else:
        tenant_key = f"user:{sub}"
        role = "admin"          # sole owner of their own workspace
        display_name = "My Workspace"

    tenant = db.query(Workspace).filter(Workspace.clerk_org_id == tenant_key).first()
    if not tenant:
        tenant = Workspace(
            owner_id=user.id,
            clerk_org_id=tenant_key,
            company_name=display_name,
            business_description="",
        )
        db.add(tenant)
        db.flush()

    member = (
        db.query(TenantMember)
        .filter(TenantMember.workspace_id == tenant.id, TenantMember.clerk_user_id == sub)
        .first()
    )
    if not member:
        db.add(TenantMember(workspace_id=tenant.id, clerk_user_id=sub, email=email, role=role))
    elif member.role != role:
        member.role = role

    db.commit()
    db.refresh(tenant)
    return AuthContext(user=user, tenant=tenant, clerk_user_id=sub, role=role)


async def get_auth_context(
    claims: dict = Depends(verify_clerk_token),
    db: Session = Depends(get_db),
) -> AuthContext:
    return provision(db, claims)


async def get_current_user(ctx: AuthContext = Depends(get_auth_context)) -> User:
    """Backwards-compatible dependency for endpoints that only need the user."""
    return ctx.user


def require_role(*roles: str):
    """Dependency factory: gate an endpoint to the given org role(s)."""
    async def _dep(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if ctx.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return ctx
    return _dep


def get_tenant_db(ctx: AuthContext = Depends(get_auth_context)):
    """Yield an RLS-scoped DB session bound to the caller's tenant. Use this for
    all tenant DATA access so Row-Level Security is enforced."""
    with tenant_context(ctx.tenant_id) as db:
        yield db
