"""Trust layer: a write-once file vault and an append-only, hash-chained ledger.

Every original file is stored under its SHA-256 and never overwritten.
Every rule approval, check, override and sign-off is appended to the ledger.
Each ledger entry hashes the previous entry's hash, so editing or deleting
any past entry breaks the chain and `verify_chain` reports where.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import now_iso

GENESIS = "0" * 64


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


class FileVault:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, digest: str) -> Path:
        return self.root / digest[:2] / digest

    def put(self, data: bytes) -> str:
        """Store bytes once. Returns the SHA-256. Re-storing identical bytes is a no-op."""
        digest = sha256_bytes(data)
        path = self.path_for(digest)
        if path.exists():
            if sha256_bytes(path.read_bytes()) != digest:
                raise RuntimeError(f"vault object {digest} has been altered on disk")
            return digest
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IRGRP)  # read-only
        return digest

    def get(self, digest: str) -> bytes:
        data = self.path_for(digest).read_bytes()
        if sha256_bytes(data) != digest:
            raise RuntimeError(f"vault object {digest} failed its integrity check")
        return data


@dataclass
class ChainReport:
    ok: bool
    entries: int
    first_bad_id: int | None = None
    reason: str = ""


class Ledger:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _last_hash(self) -> str:
        r = self.conn.execute("SELECT hash FROM ledger ORDER BY id DESC LIMIT 1").fetchone()
        return r["hash"] if r else GENESIS

    @staticmethod
    def _entry_hash(prev_hash: str, at: str, actor: str, action: str, entity: str,
                    entity_id: str | None, payload_json: str) -> str:
        body = "|".join([prev_hash, at, actor, action, entity, entity_id or "", payload_json])
        return sha256_bytes(body.encode())

    def append(self, actor: str, action: str, entity: str, entity_id: Any = None,
               payload: dict[str, Any] | None = None) -> str:
        at = now_iso()
        payload_json = _canonical(payload or {})
        prev = self._last_hash()
        eid = None if entity_id is None else str(entity_id)
        digest = self._entry_hash(prev, at, actor, action, entity, eid, payload_json)
        self.conn.execute(
            "INSERT INTO ledger (at, actor, action, entity, entity_id, payload_json, prev_hash, hash)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (at, actor, action, entity, eid, payload_json, prev, digest),
        )
        return digest

    def verify_chain(self) -> ChainReport:
        prev = GENESIS
        count = 0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY id"):
            count += 1
            if r["prev_hash"] != prev:
                return ChainReport(False, count, r["id"], "previous-hash link broken")
            expected = self._entry_hash(r["prev_hash"], r["at"], r["actor"], r["action"],
                                        r["entity"], r["entity_id"], r["payload_json"])
            if expected != r["hash"]:
                return ChainReport(False, count, r["id"], "entry content does not match its hash")
            prev = r["hash"]
        return ChainReport(True, count)
