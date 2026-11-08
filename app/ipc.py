"""Interim Payment Certificate checks (M5) and the line state machine.

claimed -> complete | exception -> reviewed | held -> certified
Only people move a line past 'complete' or 'exception'.
"""
from __future__ import annotations

import json
import sqlite3

from . import materials
from .db import insert, now_iso, row, rows, update
from .ledger import Ledger
from .roles import require_role

QTY_TOLERANCE = 0.005  # 0.5% rounding allowance on quantities


def create_ipc(conn: sqlite3.Connection, ledger: Ledger, contract_id: int, number: int, period_end: str,
               actor: str) -> int:
    iid = insert(conn, "ipcs", {"contract_id": contract_id, "number": number, "period_end": period_end,
                                "status": "draft"})
    ledger.append(actor, "ipc.created", "ipc", iid, {"number": number, "period_end": period_end})
    return iid


def add_line(conn: sqlite3.Connection, ledger: Ledger, ipc_id: int, actor: str, boq_code: str, quantity: float,
             ch_from: float | None = None, ch_to: float | None = None, description: str = "") -> int:
    ipc = row(conn, "SELECT * FROM ipcs WHERE id = ?", (ipc_id,))
    if not ipc or ipc["status"] == "certified":
        raise ValueError("Lines can only be added to an uncertified IPC")
    lid = insert(conn, "ipc_lines", {"ipc_id": ipc_id, "boq_code": boq_code, "description": description,
                                     "ch_from": ch_from, "ch_to": ch_to, "quantity": quantity, "status": "claimed"})
    ledger.append(actor, "ipc.line_claimed", "ipc_line", lid, {"boq_code": boq_code, "quantity": quantity,
                                                               "ch_from": ch_from, "ch_to": ch_to})
    return lid


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def _uncovered(lo: float, hi: float, intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    gaps, cur = [], lo
    for s, e in sorted(intervals):
        if e <= cur:
            continue
        if s > cur:
            gaps.append((cur, min(s, hi)))
        cur = max(cur, e)
        if cur >= hi:
            break
    if cur < hi:
        gaps.append((cur, hi))
    return [(a, b) for a, b in gaps if b - a > 1e-6]


def lots_touching(conn: sqlite3.Connection, contract_id: int, boq_code: str, lo: float, hi: float) -> list[dict]:
    """Lots that genuinely share ground with [lo, hi]. Touching end to end does not count."""
    cands = rows(conn, """SELECT * FROM lots WHERE contract_id = ? AND boq_code = ? AND ch_to >= ? AND ch_from <= ?
                          ORDER BY ch_from""", (contract_id, boq_code, lo, hi))
    out = []
    for l in cands:
        if lo == hi or l["ch_from"] == l["ch_to"]:
            out.append(l)  # point claim or point structure: containment is enough
        elif _overlap(lo, hi, l["ch_from"], l["ch_to"]) > 1e-6:
            out.append(l)
    return out


def check_line(conn: sqlite3.Connection, contract_id: int, ipc: dict, line: dict) -> list[dict]:
    """Return findings for one line. Each finding: {check, result, message}."""
    f: list[dict] = []
    boq = row(conn, "SELECT * FROM boq_items WHERE contract_id = ? AND code = ?", (contract_id, line["boq_code"]))
    if not boq:
        return [{"check": "boq", "result": "fail", "message": f"BOQ item {line['boq_code']} not in contract"}]

    prior = rows(conn, """SELECT l.*, i.number FROM ipc_lines l JOIN ipcs i ON i.id = l.ipc_id
                          WHERE i.contract_id = ? AND l.boq_code = ? AND l.status = 'certified' AND l.ipc_id != ?""",
                 (contract_id, line["boq_code"], ipc["id"]))
    to_date = sum(p["quantity"] for p in prior) + line["quantity"]
    if to_date > boq["quantity"] * (1 + QTY_TOLERANCE):
        f.append({"check": "boq_quantity", "result": "fail",
                  "message": f"cumulative {to_date:g} {boq['unit']} exceeds BOQ quantity {boq['quantity']:g}"})

    has_range = line["ch_from"] is not None and line["ch_to"] is not None
    if has_range:
        lo, hi = line["ch_from"], line["ch_to"]
        for p in prior:
            if p["ch_from"] is None:
                continue
            ov = _overlap(lo, hi, p["ch_from"], p["ch_to"])
            same_point = lo == hi and p["ch_from"] <= lo <= p["ch_to"]
            if ov > 1e-6 or same_point:
                f.append({"check": "duplicate", "result": "fail",
                          "message": f"ch {max(lo, p['ch_from']):g}-{min(hi, p['ch_to']):g} already certified in IPC {p['number']}"})

    qc_controlled = row(conn, """SELECT COUNT(*) AS n FROM rules WHERE contract_id = ? AND boq_code = ?
                                 AND status IN ('approved', 'superseded')""", (contract_id, line["boq_code"]))["n"] > 0
    if qc_controlled:
        if not has_range:
            f.append({"check": "location", "result": "fail",
                      "message": "quality-controlled item claimed without a chainage, so it cannot be traced to tested lots"})
        else:
            lo, hi = line["ch_from"], line["ch_to"]
            lots = lots_touching(conn, contract_id, line["boq_code"], lo, hi)
            approved = [l for l in lots if l["status"] == "approved"]
            if lo == hi:
                covered_qty = sum(l["quantity"] for l in approved)
                gaps = [] if approved else [(lo, hi)]
            else:
                covered_qty = 0.0
                for l in approved:
                    length = l["ch_to"] - l["ch_from"]
                    covered_qty += l["quantity"] * (_overlap(lo, hi, l["ch_from"], l["ch_to"]) / length if length else 1)
                gaps = _uncovered(lo, hi, [(l["ch_from"], l["ch_to"]) for l in approved])
            for g0, g1 in gaps:
                blocking = [l for l in lots if l["status"] != "approved" and l["ch_to"] >= g0 and l["ch_from"] <= g1]
                why = ", ".join(f"lot {l['id']} is {l['status']}" for l in blocking) or "no lot recorded"
                f.append({"check": "qc_coverage", "result": "fail",
                          "message": f"ch {g0:g}-{g1:g} has no released lot ({why})"})
            if line["quantity"] > covered_qty * (1 + QTY_TOLERANCE) + 1e-9:
                f.append({"check": "qc_quantity", "result": "fail",
                          "message": f"claimed {line['quantity']:g} but released lots support {covered_qty:.2f} {boq['unit']}"})
            lot_ids = [l["id"] for l in lots]
            if lot_ids:
                marks = ",".join("?" * len(lot_ids))
                n_open = row(conn, f"SELECT COUNT(*) AS n FROM ncrs WHERE status = 'open' AND lot_id IN ({marks})",
                             lot_ids)["n"]
                if n_open:
                    f.append({"check": "open_ncr", "result": "fail",
                              "message": f"{n_open} open NCR(s) on lots in this range"})

    for v in materials.consumption_variance(conn, contract_id, line["boq_code"]):
        if v["result"] == "fail":
            f.append({"check": "consumption", "result": "fail",
                      "message": f"{v['material']}: issued {v['issued']:g} vs expected {v['expected']:g} "
                                 f"{v['unit']} ({v['variance_pct']:+.1f}%), {v['message']}"})
    if not f:
        f.append({"check": "all", "result": "pass", "message": "evidence complete"})
    return f


def check_ipc(conn: sqlite3.Connection, ledger: Ledger, ipc_id: int, actor: str) -> dict:
    ipc = row(conn, "SELECT * FROM ipcs WHERE id = ?", (ipc_id,))
    if not ipc or ipc["status"] == "certified":
        raise ValueError("IPC not found or already certified")
    summary = {"complete": 0, "exception": 0}
    for line in rows(conn, "SELECT * FROM ipc_lines WHERE ipc_id = ?", (ipc_id,)):
        if line["status"] in ("reviewed", "held", "certified"):
            continue
        findings = check_line(conn, ipc["contract_id"], ipc, line)
        status = "complete" if all(x["result"] == "pass" for x in findings) else "exception"
        summary[status] += 1
        update(conn, "ipc_lines", line["id"], {"status": status, "findings_json": json.dumps(findings)})
    update(conn, "ipcs", ipc_id, {"status": "checked"})
    ledger.append(actor, "ipc.checked", "ipc", ipc_id, summary)
    return summary


def review_line(conn: sqlite3.Connection, ledger: Ledger, line_id: int, actor: str, role: str,
                decision: str, note: str = "") -> None:
    require_role(role, "review_line")
    line = row(conn, "SELECT * FROM ipc_lines WHERE id = ?", (line_id,))
    if not line or line["status"] not in ("complete", "exception", "reviewed", "held"):
        raise ValueError("Run the IPC check before reviewing lines")
    if decision not in ("accept", "hold"):
        raise ValueError("Decision must be accept or hold")
    if decision == "accept" and line["status"] == "exception" and not note.strip():
        raise ValueError("Accepting a line with exceptions is an override and needs a written reason")
    new = "reviewed" if decision == "accept" else "held"
    update(conn, "ipc_lines", line_id, {"status": new, "reviewer": actor, "review_note": note,
                                        "reviewed_at": now_iso()})
    ledger.append(actor, "ipc.line_reviewed", "ipc_line", line_id,
                  {"decision": decision, "was": line["status"], "override": line["status"] == "exception" and decision == "accept",
                   "note": note})


def certify_ipc(conn: sqlite3.Connection, ledger: Ledger, ipc_id: int, actor: str, role: str) -> dict:
    require_role(role, "certify_ipc")
    ipc = row(conn, "SELECT * FROM ipcs WHERE id = ?", (ipc_id,))
    if not ipc or ipc["status"] == "certified":
        raise ValueError("IPC not found or already certified")
    lines = rows(conn, "SELECT * FROM ipc_lines WHERE ipc_id = ?", (ipc_id,))
    pending = [l for l in lines if l["status"] not in ("reviewed", "held")]
    if pending:
        raise ValueError(f"{len(pending)} line(s) not yet reviewed by a person")
    for l in lines:
        if l["status"] == "reviewed":
            update(conn, "ipc_lines", l["id"], {"status": "certified"})
    update(conn, "ipcs", ipc_id, {"status": "certified", "certified_by": actor, "certified_at": now_iso()})
    out = {"certified": sum(l["status"] == "reviewed" for l in lines), "held": sum(l["status"] == "held" for l in lines)}
    ledger.append(actor, "ipc.certified", "ipc", ipc_id, out)
    return out


def evidence_pack(conn: sqlite3.Connection, ipc_id: int) -> dict:
    ipc = row(conn, "SELECT * FROM ipcs WHERE id = ?", (ipc_id,))
    contract = row(conn, "SELECT * FROM contracts WHERE id = ?", (ipc["contract_id"],))
    lines = rows(conn, """SELECT l.*, b.description AS boq_description, b.unit, b.rate
                          FROM ipc_lines l LEFT JOIN boq_items b ON b.code = l.boq_code AND b.contract_id = ?
                          WHERE l.ipc_id = ? ORDER BY l.id""", (ipc["contract_id"], ipc_id))
    for l in lines:
        l["findings"] = json.loads(l["findings_json"] or "[]")
        l["amount"] = round((l["rate"] or 0) * l["quantity"], 2)
        if l["ch_from"] is not None:
            l["lots"] = lots_touching(conn, ipc["contract_id"], l["boq_code"], l["ch_from"], l["ch_to"])
        else:
            l["lots"] = []
    payable = sum(l["amount"] for l in lines if l["status"] in ("certified", "reviewed"))
    held = sum(l["amount"] for l in lines if l["status"] == "held")
    return {"ipc": ipc, "contract": contract, "lines": lines, "payable": round(payable, 2), "held": round(held, 2)}
