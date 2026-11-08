"""Document intake: web upload and the WhatsApp Business Platform webhook.

Every file goes into the write-once vault first, then gets a document record.
The WhatsApp handlers follow Meta's Cloud API webhook format; they are not yet
tested against a live number.
"""
from __future__ import annotations

import hashlib
import hmac
import mimetypes
import re
import sqlite3

from . import licences
from .config import Settings
from .db import insert, now_iso
from .ledger import FileVault, Ledger

KINDS = ("lab_report", "supplier_cert", "waybill", "spec", "standard", "claim", "other")

CAPTION_KINDS = {
    "lab": "lab_report", "test": "lab_report", "cert": "supplier_cert", "mill": "supplier_cert",
    "waybill": "waybill", "delivery": "waybill", "spec": "spec", "claim": "claim", "ipc": "claim",
}


def store_document(conn: sqlite3.Connection, vault: FileVault, ledger: Ledger, *, contract_id: int, actor: str,
                   data: bytes, filename: str, kind: str, source: str = "upload", mime: str | None = None,
                   publisher: str | None = None, caption: str = "") -> int:
    if kind not in KINDS:
        raise ValueError(f"Unknown document kind '{kind}'")
    if not data:
        raise ValueError("The file is empty")
    if kind == "standard":
        if not publisher:
            raise ValueError("Say which publisher the standard is from")
        licences.require(conn, publisher, "store")
    digest = vault.put(data)
    did = insert(conn, "documents", {
        "contract_id": contract_id, "kind": kind, "filename": filename, "sha256": digest, "size": len(data),
        "mime": mime or mimetypes.guess_type(filename)[0], "source": source,
        "publisher": licences.normalise(publisher) if publisher else None, "caption": caption,
        "received_at": now_iso(), "status": "received",
    })
    ledger.append(actor, "document.received", "document", did,
                  {"sha256": digest, "kind": kind, "filename": filename, "source": source})
    return did


def kind_from_caption(caption: str) -> str:
    words = re.findall(r"[a-z]+", (caption or "").lower())
    for w in words:
        if w in CAPTION_KINDS:
            return CAPTION_KINDS[w]
    return "other"


def verify_signature(settings: Settings, body: bytes, header: str | None) -> bool:
    """Check Meta's X-Hub-Signature-256 header with the app secret."""
    if not settings.whatsapp_app_secret:
        return False
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


def parse_media_messages(payload: dict) -> list[dict]:
    """Pull image and document messages out of a WhatsApp webhook payload."""
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []) or []:
                mtype = msg.get("type")
                if mtype not in ("image", "document"):
                    continue
                media = msg.get(mtype, {})
                out.append({
                    "from": msg.get("from", ""), "message_id": msg.get("id", ""), "media_id": media.get("id"),
                    "mime": media.get("mime_type"), "filename": media.get("filename") or f"{msg.get('id', 'media')}.{mtype}",
                    "caption": media.get("caption", ""),
                })
    return out


def download_media(settings: Settings, media_id: str) -> tuple[bytes, str | None]:
    import httpx
    if not settings.whatsapp_access_token:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not set")
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    base = f"https://graph.facebook.com/{settings.whatsapp_graph_version}"
    with httpx.Client(timeout=30) as http:
        meta = http.get(f"{base}/{media_id}", headers=headers)
        meta.raise_for_status()
        info = meta.json()
        file = http.get(info["url"], headers=headers)
        file.raise_for_status()
        return file.content, info.get("mime_type")
