"""Materials chain checks M1 to M4: order, delivery, store and use against design.

M5 (claim is supported) lives in ipc.py because it runs per payment line.
"""
from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass

from .db import rows


@dataclass
class Check:
    code: str
    ref: str
    result: str      # pass | fail | marginal
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def check_orders(conn: sqlite3.Connection, contract_id: int) -> list[Check]:
    """M1: each purchase order is for an approved supplier and grade."""
    out = []
    sources = rows(conn, "SELECT * FROM approved_sources WHERE contract_id = ?", (contract_id,))
    for po in rows(conn, "SELECT * FROM purchase_orders WHERE contract_id = ?", (contract_id,)):
        ok_sources = [s for s in sources if _norm(s["material"]) == _norm(po["material"])]
        if not ok_sources:
            out.append(Check("M1", po["po_ref"], "fail", f"No approved source recorded for {po['material']}"))
            continue
        match = [s for s in ok_sources if _norm(s["supplier"]) == _norm(po["supplier"])
                 and (not s["grade"] or _norm(s["grade"]) == _norm(po["grade"]))]
        if match:
            out.append(Check("M1", po["po_ref"], "pass", f"{po['supplier']} {po['grade'] or ''} is approved"))
        else:
            out.append(Check("M1", po["po_ref"], "fail",
                             f"{po['supplier']} {po['grade'] or ''} is not an approved source for {po['material']}"))
    return out


def check_deliveries(conn: sqlite3.Connection, contract_id: int) -> list[Check]:
    """M2: each delivery matches its order, certificate and marking."""
    out = []
    pos = {p["po_ref"]: p for p in rows(conn, "SELECT * FROM purchase_orders WHERE contract_id = ?", (contract_id,))}
    delivered: dict[str, float] = {}
    for d in rows(conn, "SELECT * FROM deliveries WHERE contract_id = ? ORDER BY delivered_on, id", (contract_id,)):
        ref = d["waybill_no"]
        po = pos.get(d["po_ref"] or "")
        problems = []
        if not po:
            problems.append("no matching purchase order")
        else:
            if _norm(po["supplier"]) != _norm(d["supplier"]):
                problems.append(f"supplier {d['supplier']} differs from order ({po['supplier']})")
            if _norm(po["material"]) != _norm(d["material"]):
                problems.append(f"material {d['material']} differs from order ({po['material']})")
            if po["grade"] and _norm(po["grade"]) != _norm(d["grade"]):
                problems.append(f"grade {d['grade']} differs from order ({po['grade']})")
            delivered[po["po_ref"]] = delivered.get(po["po_ref"], 0) + d["quantity"]
            if delivered[po["po_ref"]] > po["quantity"] * 1.0001:
                problems.append(f"cumulative deliveries {delivered[po['po_ref']]:g} exceed order {po['quantity']:g} {po['unit']}")
        if d["heat_no"] or d["cert_heat_no"]:
            if not d["cert_heat_no"]:
                problems.append("no mill certificate heat number recorded")
            elif _norm(d["heat_no"]) != _norm(d["cert_heat_no"]):
                problems.append(f"bar tag heat {d['heat_no']} does not match certificate heat {d['cert_heat_no']}")
        if "rebar" in _norm(d["material"]) or "reinforc" in _norm(d["material"]):
            if not d["gsa_marked"]:
                problems.append("rebar delivered without GSA marking recorded")
        out.append(Check("M2", ref, "fail" if problems else "pass",
                         "; ".join(problems) if problems else "matches order, certificate and marking"))
    return out


def store_balances(conn: sqlite3.Connection, contract_id: int) -> list[dict]:
    """M3: received minus issued against the latest physical count."""
    out = []
    mats = rows(conn, "SELECT DISTINCT material, unit FROM store_moves WHERE contract_id = ?", (contract_id,))
    for m in mats:
        moves = rows(conn, "SELECT * FROM store_moves WHERE contract_id = ? AND material = ? ORDER BY moved_on, id",
                     (contract_id, m["material"]))
        received = sum(x["quantity"] for x in moves if x["direction"] == "in")
        issued = sum(x["quantity"] for x in moves if x["direction"] == "out")
        counts = [x for x in moves if x["direction"] == "count"]
        book = received - issued
        last = counts[-1] if counts else None
        diff = None if last is None else last["quantity"] - book
        result = "pass"
        msg = f"book balance {book:g} {m['unit']}"
        if last is not None and abs(diff) > 1e-9:
            result = "fail"
            msg += f"; count on {last['moved_on']} found {last['quantity']:g} ({diff:+g})"
        elif last is None:
            result = "marginal"
            msg += "; no physical count recorded"
        out.append({"code": "M3", "material": m["material"], "unit": m["unit"], "received": received,
                    "issued": issued, "book": book, "counted": None if last is None else last["quantity"],
                    "difference": diff, "result": result, "message": msg})
    return out


def consumption_variance(conn: sqlite3.Connection, contract_id: int, boq_code: str | None = None,
                         installed: dict[str, float] | None = None) -> list[dict]:
    """M4: material issued to a BOQ item against installed quantity x design rate.

    Installed quantity defaults to the sum of the item's lot quantities.
    Issued well above expected suggests loss; below expected suggests under-dosing.
    """
    out = []
    q = "SELECT * FROM consumption_rates WHERE contract_id = ?"
    params: list = [contract_id]
    if boq_code:
        q += " AND boq_code = ?"
        params.append(boq_code)
    for rate in rows(conn, q, params):
        if installed and rate["boq_code"] in installed:
            inst = installed[rate["boq_code"]]
        else:
            inst = rows(conn, "SELECT IFNULL(SUM(quantity), 0) AS q FROM lots WHERE contract_id = ? AND boq_code = ?",
                        (contract_id, rate["boq_code"]))[0]["q"]
        expected = inst * rate["rate_per_unit"]
        issued = rows(conn, """SELECT IFNULL(SUM(quantity), 0) AS q FROM store_moves WHERE contract_id = ?
                               AND material = ? AND boq_code = ? AND direction = 'out'""",
                      (contract_id, rate["material"], rate["boq_code"]))[0]["q"]
        variance = issued - expected
        pct = (variance / expected * 100) if expected else 0.0
        if abs(pct) <= rate["allowance_pct"]:
            result, meaning = "pass", "within allowance"
        elif variance < 0:
            result, meaning = "fail", "possible under-dosing; ask for extra tests on these pours"
        else:
            result, meaning = "fail", "possible waste or loss"
        out.append({"code": "M4", "boq_code": rate["boq_code"], "material": rate["material"],
                    "unit": rate["material_unit"], "installed": inst, "rate": rate["rate_per_unit"],
                    "expected": round(expected, 3), "issued": issued, "variance": round(variance, 3),
                    "variance_pct": round(pct, 2), "allowance_pct": rate["allowance_pct"], "result": result,
                    "message": meaning})
    return out
