"""HMAC verification for wacli sync webhooks.

wacli signs the raw request body with:
  X-Wacli-Signature: sha256=<hmac_hex>
where the HMAC is SHA-256 of the body using `--webhook-secret`.
"""

from __future__ import annotations

import hashlib
import hmac


def verify_wacli_signature(secret: str, raw_body: bytes, header: str | None) -> bool:
    """Return True if `header` is a valid signature for `raw_body` under `secret`."""
    if not secret or not header:
        return False
    value = header.strip()
    if value.lower().startswith("sha256="):
        value = value.split("=", 1)[1].strip()
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    # Accept hex (documented) and also raw hex without prefix already stripped above.
    try:
        return hmac.compare_digest(expected, value.lower())
    except (TypeError, ValueError):
        return False


def signature_header(secret: str, raw_body: bytes) -> str:
    """Build the header value wacli would send (for tests)."""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"
