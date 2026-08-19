"""wacli provider — near-term WhatsApp transport via the wacli CLI.

Wraps `wacli send text` / `wacli send file` (whatsmeow-backed linked device).
Callers must still pass `outreach_policy.gate()` before any send.

Per-tenant isolation: pass a distinct `--store` directory (from the number row
or `WACLI_STORE_DIR`). Templates are unsupported on this path.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Sequence

import httpx

from app.core.config import settings
from app.messaging.base import MessagingProvider, OutgoingMedia, SendResult

logger = logging.getLogger(__name__)


class WacliProvider(MessagingProvider):
    def __init__(
        self,
        store_dir: Optional[str] = None,
        binary: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.store_dir = store_dir or (settings.WACLI_STORE_DIR or "").strip() or None
        self.binary = binary or settings.WACLI_BIN or "wacli"
        self.timeout = timeout if timeout is not None else float(settings.WACLI_TIMEOUT_SECONDS)

    def _base_cmd(self) -> list[str]:
        cmd = [self.binary, "--json"]
        if self.store_dir:
            cmd.extend(["--store", self.store_dir])
        if self.timeout and self.timeout > 0:
            # wacli --timeout accepts Go durations, e.g. "60s"
            cmd.extend(["--timeout", f"{int(self.timeout)}s"])
        return cmd

    def _run(self, args: Sequence[str], log_ctx: str) -> SendResult:
        cmd = self._base_cmd() + list(args)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 5 if self.timeout else None,
                check=False,
            )
        except FileNotFoundError:
            logger.error("[wacli/%s] binary not found: %s", log_ctx, self.binary)
            return SendResult(False, error=f"wacli_binary_not_found:{self.binary}")
        except subprocess.TimeoutExpired:
            logger.error("[wacli/%s] timed out after %ss", log_ctx, self.timeout)
            return SendResult(False, error="wacli_timeout")

        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        if proc.returncode != 0:
            err = stderr or stdout or f"exit_{proc.returncode}"
            logger.error("[wacli/%s] rc=%s err=%s", log_ctx, proc.returncode, err)
            return SendResult(False, error=err[:500])

        msg_id = _parse_message_id(stdout)
        if stdout:
            try:
                payload = json.loads(stdout)
                if isinstance(payload, dict) and payload.get("sent") is False:
                    return SendResult(
                        False,
                        error=str(payload.get("error") or payload.get("message") or "wacli_send_failed"),
                    )
            except json.JSONDecodeError:
                pass

        return SendResult(True, wa_message_id=msg_id)

    def send_text(self, to: str, text: str) -> SendResult:
        if not to or not text:
            return SendResult(False, error="missing_to_or_text")
        return self._run(
            ["send", "text", "--to", _normalize_recipient(to), "--message", text],
            "send_text",
        )

    def send_media(self, to: str, media: OutgoingMedia, caption: Optional[str] = None) -> SendResult:
        if not to:
            return SendResult(False, error="missing_to")

        cleanup: Optional[Path] = None
        try:
            path = media.path
            if not path and media.url:
                cleanup = _download_to_temp(media.url, media.mime)
                path = str(cleanup)
            if not path:
                return SendResult(False, error="media_missing_path_and_url")

            args = [
                "send",
                "file",
                "--to",
                _normalize_recipient(to),
                "--file",
                path,
            ]
            if caption:
                args.extend(["--caption", caption])
            if media.mime:
                args.extend(["--mime", media.mime])
            if media.kind in ("image", "video", "audio", "document"):
                args.extend(["--as", media.kind])

            return self._run(args, "send_media")
        finally:
            if cleanup is not None:
                try:
                    cleanup.unlink(missing_ok=True)
                except OSError:
                    pass

    def send_template(
        self, to: str, template: str, language: str, variables: Optional[dict] = None
    ) -> SendResult:
        return SendResult(False, error="templates_unsupported_on_wacli")

    def send_typing(self, to: str, on: bool = True) -> None:
        # wacli has chat_presence sync events but no first-class "send typing" command
        # in current releases — no-op; pacing stays in typing_delay.
        return None


def _normalize_recipient(to: str) -> str:
    """Accept JID or phone; strip whatsapp suffixes for phone-style targets."""
    value = (to or "").strip()
    if "@" in value:
        return value
    digits = "".join(ch for ch in value if ch.isdigit() or ch == "+")
    return digits or value


def _parse_message_id(stdout: str) -> Optional[str]:
    if not stdout:
        return None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("id", "ID", "message_id", "messageId", "msg_id"):
        if payload.get(key):
            return str(payload[key])
    # Nested shapes seen in some CLI versions
    for nest in ("message", "data", "result"):
        inner = payload.get(nest)
        if isinstance(inner, dict):
            for key in ("id", "ID"):
                if inner.get(key):
                    return str(inner[key])
    return None


def _download_to_temp(url: str, mime: Optional[str] = None) -> Path:
    suffix = ".bin"
    if mime:
        if "jpeg" in mime or "jpg" in mime:
            suffix = ".jpg"
        elif "png" in mime:
            suffix = ".png"
        elif "webp" in mime:
            suffix = ".webp"
        elif "mp4" in mime or "video" in mime:
            suffix = ".mp4"
        elif "pdf" in mime:
            suffix = ".pdf"
    fd, name = tempfile.mkstemp(prefix="wacli-media-", suffix=suffix)
    path = Path(name)
    try:
        import os

        os.close(fd)
        with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as res:
            res.raise_for_status()
            with path.open("wb") as out:
                for chunk in res.iter_bytes():
                    out.write(chunk)
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def resolve_store_dir(
    store_dir: Optional[str] = None,
    account: Optional[str] = None,
) -> Optional[str]:
    """Resolve the wacli --store path for a number.

    Prefer an explicit store_dir; else if `account` is set, use
    `{WACLI_STORE_DIR or ~/.wacli}/accounts/{account}`.
    """
    if store_dir:
        return store_dir
    global_store = (settings.WACLI_STORE_DIR or "").strip() or None
    if account:
        base = global_store or str(Path.home() / ".wacli")
        return str(Path(base) / "accounts" / account)
    return global_store


def wacli_available(binary: Optional[str] = None) -> bool:
    return shutil.which(binary or settings.WACLI_BIN or "wacli") is not None
