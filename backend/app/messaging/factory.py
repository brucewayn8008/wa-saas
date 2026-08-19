"""Resolve the right MessagingProvider for a connected WhatsApp number.

Callers pass a duck-typed `number` object (a `wa_numbers` row or shim) exposing:
    provider            : "wacli" | "whatsmeow" | "cloud_api"
    wacli_store_dir     : str   (optional — wacli --store)
    wacli_account       : str   (optional — subdirectory under store base)
    phone_number_id     : str   (cloud_api, deferred)
    access_token        : str   (cloud_api, deferred)
    workspace_id / id   : str   (whatsmeow routing key)
"""

from __future__ import annotations

from app.messaging.base import MessagingProvider
from app.messaging.cloud_api import CloudApiProvider
from app.messaging.wacli import WacliProvider, resolve_store_dir
from app.messaging.whatsmeow import WhatsmeowProvider


def get_provider(number) -> MessagingProvider:
    provider = getattr(number, "provider", None) or "wacli"

    if provider == "wacli":
        store = resolve_store_dir(
            store_dir=getattr(number, "wacli_store_dir", None),
            account=getattr(number, "wacli_account", None),
        )
        return WacliProvider(store_dir=store)

    if provider == "cloud_api":
        return CloudApiProvider(
            phone_number_id=getattr(number, "phone_number_id"),
            access_token=getattr(number, "access_token"),
        )

    workspace_id = getattr(number, "workspace_id", None) or getattr(number, "id", None)
    return WhatsmeowProvider(workspace_id=str(workspace_id))
