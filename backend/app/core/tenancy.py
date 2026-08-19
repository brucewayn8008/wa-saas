"""Tenant context for Row-Level Security.

Every tenant-scoped DB access must run inside `tenant_context(tenant_id)`, which
opens a session and sets the Postgres `app.tenant_id` GUC. RLS policies on tenant
tables filter on `current_setting('app.tenant_id')`, so a query without this set
returns nothing (fail-closed) once RLS is enabled (Feature 02 migration).

Setting the GUC is harmless before RLS is enabled, so this helper is safe to adopt now.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def set_tenant(db: Session, tenant_id: str) -> None:
    """Set the RLS GUC for the current transaction. Uses set_config to bind the
    value safely (no string interpolation into SQL)."""
    db.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


@contextmanager
def tenant_context(tenant_id: str) -> Generator[Session, None, None]:
    """Yield a DB session scoped to a single tenant.

    Usage:
        with tenant_context(tenant_id) as db:
            db.query(Lead)...   # RLS-scoped to this tenant
    """
    db = SessionLocal()
    try:
        set_tenant(db, tenant_id)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
