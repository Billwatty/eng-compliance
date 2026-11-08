"""Monthly quality report: tests done against required, pass rates, spread, NCRs and verification share."""
from __future__ import annotations

import json
import sqlite3
from statistics import mean, pstdev

from .db import rows
from .rules import required_tests


def monthly_quality_report(conn: sqlite3.Connection, contract_id: int, month: str) -> dict:
    """month = 'YYYY-MM'. Covers lots placed in that month."""
    lots = rows(conn, "SELECT * FROM lots WHERE contract_id = ? AND substr(placed_on, 1, 7) = ?", (contract_id, month))
    lot_ids = [l["id"] for l in lots]
    by_param: dict[tuple[str, str], dict] = {}
    for l in lots:
        rules = rows(conn, """SELECT * FROM rules WHERE contract_id = ? AND boq_code = ?
                              AND status IN ('approved', 'superseded') AND effective_from <= ?""",
                     (contract_id, l["boq_code"], l["placed_on"]))
        seen = set()
        for r in rules:
            if r["rule_code"] in seen:
                continue
            seen.add(r["rule_code"])
            key = (l["boq_code"], r["parameter"])
            agg = by_param.setdefault(key, {"boq_code": l["boq_code"], "parameter": r["parameter"], "unit": r["unit"],
                                             "required": 0, "done": 0, "values": [], "by_consultant": 0})
            if r["limit_type"] == "envelope":
                ts = rows(conn, "SELECT * FROM tests WHERE lot_id = ? AND parameter LIKE ?", (l["id"], r["parameter"] + ":%"))
                n = len({t["group_ref"] or t["id"] for t in ts})
            elif r["limit_type"] == "concrete_cube":
                ts = rows(conn, "SELECT * FROM tests WHERE lot_id = ? AND parameter = ?", (l["id"], r["parameter"]))
                n = len({t["group_ref"] or t["id"] for t in ts})
            else:
                ts = rows(conn, "SELECT * FROM tests WHERE lot_id = ? AND parameter = ?", (l["id"], r["parameter"]))
                n = len(ts)
                agg["values"].extend(t["value"] for t in ts)
            if r["frequency_qty"]:
                agg["required"] += required_tests(l["lot_size"], r["frequency_qty"])
            agg["done"] += n
            agg["by_consultant"] += sum(1 for t in ts if t["performed_by"] != "contractor_qc")
    lines = []
    for agg in by_param.values():
        vals = agg.pop("values")
        agg["mean"] = round(mean(vals), 2) if vals else None
        agg["spread"] = round(pstdev(vals), 2) if len(vals) > 1 else None
        agg["verification_pct"] = round(100 * agg["by_consultant"] / agg["done"], 1) if agg["done"] else 0.0
        lines.append(agg)
    single_pass = single_total = 0
    for lid in lot_ids:
        ev = rows(conn, "SELECT findings_json FROM evaluations WHERE lot_id = ? ORDER BY id DESC LIMIT 1", (lid,))
        if ev:
            for f in json.loads(ev[0]["findings_json"]):
                if f["kind"] in ("single", "tolerance", "envelope", "concrete_individual"):
                    single_total += 1
                    single_pass += f["result"] != "fail"
    status_counts: dict[str, int] = {}
    for l in lots:
        status_counts[l["status"]] = status_counts.get(l["status"], 0) + 1
    ncrs_open = rows(conn, "SELECT * FROM ncrs WHERE contract_id = ? AND status = 'open' ORDER BY raised_at", (contract_id,))
    ncrs_month = rows(conn, "SELECT COUNT(*) AS n FROM ncrs WHERE contract_id = ? AND substr(raised_at, 1, 7) = ?",
                      (contract_id, month))[0]["n"]
    return {"month": month, "lots": lots, "status_counts": status_counts, "lines": sorted(lines, key=lambda x: (x["boq_code"], x["parameter"])),
            "pass_rate": round(100 * single_pass / single_total, 1) if single_total else None,
            "ncrs_open": ncrs_open, "ncrs_raised": ncrs_month}
