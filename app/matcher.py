"""Link extracted documents to lots. Exact keys link automatically; anything else goes to review."""
from __future__ import annotations

import sqlite3

from .db import rows


def match_lab_report(conn: sqlite3.Connection, contract_id: int, extract: dict) -> dict:
    tags = {t.strip() for t in extract.get("sample_tags") or [] if t and t.strip()}
    tags |= {r.get("sample_tag").strip() for r in extract.get("results") or [] if r.get("sample_tag")}
    if tags:
        marks = ",".join("?" * len(tags))
        hits = rows(conn, f"""SELECT s.tag_id, s.lot_id FROM samples s JOIN lots l ON l.id = s.lot_id
                              WHERE l.contract_id = ? AND s.tag_id IN ({marks})""", [contract_id, *tags])
        lots = sorted({h["lot_id"] for h in hits})
        if len(lots) == 1:
            missing = sorted(tags - {h["tag_id"] for h in hits})
            conf = 1.0 if not missing else 0.8
            return {"lot_id": lots[0], "confidence": conf, "candidates": lots,
                    "reason": "sample tag match" + (f"; unknown tags {', '.join(missing)}" if missing else "")}
        if len(lots) > 1:
            return {"lot_id": None, "confidence": 0.4, "candidates": lots,
                    "reason": "sample tags belong to more than one lot"}
    lo = extract.get("chainage_from_m")
    hi = extract.get("chainage_to_m") if extract.get("chainage_to_m") is not None else lo
    if lo is not None:
        cands = rows(conn, """SELECT id, layer FROM lots WHERE contract_id = ? AND ch_from <= ? AND ch_to >= ?
                              AND status != 'approved'""", (contract_id, hi, lo))
        layer = (extract.get("layer") or "").lower()
        if layer:
            narrowed = [c for c in cands if c["layer"] and (c["layer"].lower() in layer or layer in c["layer"].lower())]
            cands = narrowed or cands
        if len(cands) == 1:
            return {"lot_id": cands[0]["id"], "confidence": 0.7, "candidates": [cands[0]["id"]],
                    "reason": "chainage match only; confirm the lot"}
        if cands:
            return {"lot_id": None, "confidence": 0.4, "candidates": [c["id"] for c in cands],
                    "reason": "chainage matches several open lots"}
    return {"lot_id": None, "confidence": 0.0, "candidates": [], "reason": "no sample tag or chainage to match on"}
