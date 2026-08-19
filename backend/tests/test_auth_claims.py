"""A1 — Clerk auth: user→tenant path (free plan) + org→tenant path (future paid).

Covers:
  - extract_org handles both Clerk token formats and the no-org case.
  - provision() derives the correct tenant_key for both free-plan and org users.
  - dev fallback produces no org claims (user path only).
"""

from unittest.mock import MagicMock, patch

from app.core.auth import AuthContext, _normalize_role, extract_org, provision


# ── extract_org ──────────────────────────────────────────────────────────────

def test_legacy_flat_claims():
    claims = {"org_id": "org_123", "org_role": "org:admin", "org_slug": "acme"}
    o = extract_org(claims)
    assert (o.org_id, o.role, o.slug) == ("org_123", "admin", "acme")


def test_v2_object_claim():
    claims = {"o": {"id": "org_456", "rol": "admin", "slg": "beta"}}
    o = extract_org(claims)
    assert (o.org_id, o.role, o.slug) == ("org_456", "admin", "beta")


def test_v2_role_with_prefix_normalized():
    o = extract_org({"o": {"id": "org_1", "rol": "org:member", "slg": "x"}})
    assert o.role == "member"


def test_no_org_returns_none():
    """Free-plan token carries no org claims → org_id must be None."""
    o = extract_org({"sub": "user_abc123"})
    assert o.org_id is None and o.role is None


def test_normalize_role():
    assert _normalize_role("org:admin") == "admin"
    assert _normalize_role("admin") == "admin"
    assert _normalize_role(None) is None
    assert _normalize_role("org:billing") == "billing"


# ── tenant key derivation ─────────────────────────────────────────────────────

def _make_db(existing_user=None, existing_workspace=None, existing_member=None):
    """Return a minimal mock Session for provision() unit tests.
    provision() makes 3 .first() calls: User → Workspace → TenantMember.
    """
    db = MagicMock()
    query = db.query.return_value
    filter_ = query.filter.return_value
    filter_.first.side_effect = [existing_user, existing_workspace, existing_member]
    return db


def test_free_plan_tenant_key_is_user_sub():
    """No org in token → role is admin, clerk_user_id is the sub."""
    user = MagicMock(id="u-1")
    workspace = MagicMock(id="ws-1")
    member = MagicMock()
    db = _make_db(existing_user=user, existing_workspace=workspace, existing_member=member)

    claims = {"sub": "user_abc", "email": "alice@example.com"}
    ctx = provision(db, claims)

    assert ctx.clerk_user_id == "user_abc"
    assert ctx.role == "admin"
    assert ctx.tenant is workspace


def test_free_plan_creates_workspace_on_first_login():
    """No existing workspace → provision() creates one with key 'user:{sub}'."""
    db = _make_db(existing_workspace=None, existing_member=None)

    # Patch User query too — second call (for member) returns None
    added = []
    db.add.side_effect = lambda obj: added.append(obj)
    db.query.return_value.filter.return_value.first.side_effect = [
        None,   # no existing User
        None,   # no existing Workspace
        None,   # no existing TenantMember
    ]
    db.flush.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None

    with patch("app.core.auth.User") as MockUser, \
         patch("app.core.auth.Workspace") as MockWorkspace:
        MockUser.return_value = MagicMock(id="u-1")
        MockWorkspace.return_value = MagicMock(id="ws-new")

        claims = {"sub": "user_xyz", "email": "bob@example.com"}
        provision(db, claims)

        # Workspace created with user-keyed clerk_org_id
        MockWorkspace.assert_called_once()
        call_kwargs = MockWorkspace.call_args.kwargs
        assert call_kwargs["clerk_org_id"] == "user:user_xyz"


def test_org_tenant_key_takes_priority_when_present():
    """If org claims exist (future paid plan), org_id is used as tenant key."""
    user = MagicMock(id="u-2")
    workspace = MagicMock(id="ws-org")
    member = MagicMock()
    db = _make_db(existing_user=user, existing_workspace=workspace, existing_member=member)

    claims = {
        "sub": "user_abc",
        "email": "alice@example.com",
        "o": {"id": "org_paid", "rol": "admin", "slg": "acme"},
    }
    ctx = provision(db, claims)

    assert ctx.clerk_user_id == "user_abc"
    assert ctx.role == "admin"
    assert ctx.tenant is workspace


def test_auth_context_exposes_clerk_user_id_not_org_id():
    """AuthContext must expose clerk_user_id (sub), not org_id."""
    user = MagicMock(id="u-3")
    workspace = MagicMock(id="ws-1")
    member = MagicMock()
    db = _make_db(existing_user=user, existing_workspace=workspace, existing_member=member)

    claims = {"sub": "user_check", "email": "check@example.com"}
    ctx = provision(db, claims)
    assert ctx.clerk_user_id == "user_check"
    assert not hasattr(ctx, "org_id")
