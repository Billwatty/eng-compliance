"""Licence register and licence gate for standards content.

A publisher's standards may be stored or processed by AI only for the uses a
signed licence permits. Until then the engineer enters numeric limits by hand.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date

from .db import insert, now_iso, rows

# Publishers whose standards need a licence before storage or AI processing.
LICENSED_PUBLISHERS = {"ISO", "ASTM", "BSI", "GSA", "AASHTO", "CEN"}
# Contract and government documents, used with the client's permission (set in the pilot agreement).
OPEN_SOURCES = {"CONTRACT", "MRH", "GHA", "TRL", "MANUAL"}

USES = ("store", "ai_extract", "store_excerpt")


class LicenceDenied(Exception):
    pass


def normalise(publisher: str) -> str:
    return (publisher or "").strip().upper()


def add_licence(conn: sqlite3.Connection, publisher: str, holder: str, uses: list[str],
                customers: str = "", expires_on: str | None = None, reference: str = "") -> int:
    bad = [u for u in uses if u not in USES]
    if bad:
        raise ValueError(f"unknown licence uses: {bad}")
    return insert(conn, "licences", {
        "publisher": normalise(publisher), "holder": holder, "uses_json": json.dumps(sorted(set(uses))),
        "customers": customers, "expires_on": expires_on or None, "reference": reference,
        "created_at": now_iso(),
    })


def active_uses(conn: sqlite3.Connection, publisher: str, on: date | None = None) -> set[str]:
    on = on or date.today()
    out: set[str] = set()
    for lic in rows(conn, "SELECT * FROM licences WHERE publisher = ?", (normalise(publisher),)):
        if lic["expires_on"] and date.fromisoformat(lic["expires_on"]) < on:
            continue
        out.update(json.loads(lic["uses_json"]))
    return out


def is_permitted(conn: sqlite3.Connection, publisher: str, use: str, on: date | None = None) -> bool:
    pub = normalise(publisher)
    if pub in OPEN_SOURCES:
        return True
    if pub not in LICENSED_PUBLISHERS:
        # Unknown publisher: treat as licensed content to be safe.
        pass
    return use in active_uses(conn, pub, on)


def require(conn: sqlite3.Connection, publisher: str, use: str) -> None:
    if not is_permitted(conn, publisher, use):
        raise LicenceDenied(
            f"No active {normalise(publisher)} licence permits '{use}'. "
            "Enter the numeric limits and clause numbers by hand from your licensed copy."
        )


def register_status(conn: sqlite3.Connection) -> list[dict]:
    out = []
    for pub in sorted(LICENSED_PUBLISHERS):
        uses = active_uses(conn, pub)
        out.append({"publisher": pub, "uses": sorted(uses),
                    "mode": "AI extraction" if "ai_extract" in uses else "Manual limit entry"})
    return out
