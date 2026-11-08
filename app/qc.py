"""Quality control: rule cards, lots, tests, evaluation, NCRs and hold points."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from . import licences
from .db import insert, now_iso, row, rows, update
from .ledger import Ledger
from .roles import require_role
from .rules import FAIL, MARGINAL, PASS, Rule, TestResult, evaluate_rule, overall, validate_params


# ---------- rule cards ----------

def add_rule(conn: sqlite3.Connection, ledger: Ledger, *, contract_id: int, actor: str, rule_code: str,
             boq_code: str, parameter: str, limit_type: str, params: dict[str, Any], source_publisher: str,
             source_ref: str, effective_from: str, unit: str = "", method: str = "",
             frequency_qty: float | None = None, marginal_band: float = 0.0, source_quote: str = "",
             drafted_by: str = "manual") -> int:
    validate_params(limit_type, params)
    pub = licences.normalise(source_publisher)
    if drafted_by == "ai":
        licences.require(conn, pub, "ai_extract")
    if source_quote and not licences.is_permitted(conn, pub, "store_excerpt"):
        # Without an excerpt licence keep numbers and clause numbers only.
        source_quote = ""
    if not source_ref.strip():
        raise ValueError("Every rule needs a clause reference")
    current = row(conn, "SELECT MAX(version) AS v FROM rules WHERE contract_id = ? AND rule_code = ?",
                  (contract_id, rule_code))
    version = (current["v"] or 0) + 1
    rid = insert(conn, "rules", {
        "contract_id": contract_id, "rule_code": rule_code, "version": version, "boq_code": boq_code,
        "parameter": parameter, "unit": unit, "method": method, "limit_type": limit_type,
        "params_json": json.dumps(params, sort_keys=True), "frequency_qty": frequency_qty,
        "marginal_band": marginal_band, "source_publisher": pub, "source_ref": source_ref,
        "source_quote": source_quote, "effective_from": effective_from, "status": "draft",
        "drafted_by": drafted_by, "created_at": now_iso(),
    })
    ledger.append(actor, "rule.drafted", "rule", rid, {"rule_code": rule_code, "version": version,
                                                       "drafted_by": drafted_by, "params": params,
                                                       "source": f"{pub} {source_ref}"})
    return rid


def approve_rule(conn: sqlite3.Connection, ledger: Ledger, rule_id: int, actor: str, role: str) -> None:
    require_role(role, "approve_rule")
    r = row(conn, "SELECT * FROM rules WHERE id = ?", (rule_id,))
    if not r or r["status"] != "draft":
        raise ValueError("Only draft rules can be approved")
    for old in rows(conn, "SELECT id FROM rules WHERE contract_id = ? AND rule_code = ? AND status = 'approved'",
                    (r["contract_id"], r["rule_code"])):
        update(conn, "rules", old["id"], {"status": "superseded"})
    update(conn, "rules", rule_id, {"status": "approved", "approved_by": actor, "approved_at": now_iso()})
    ledger.append(actor, "rule.approved", "rule", rule_id, {"rule_code": r["rule_code"], "version": r["version"],
                                                           "effective_from": r["effective_from"]})


def reject_rule(conn: sqlite3.Connection, ledger: Ledger, rule_id: int, actor: str, role: str, reason: str) -> None:
    require_role(role, "approve_rule")
    update(conn, "rules", rule_id, {"status": "rejected"})
    ledger.append(actor, "rule.rejected", "rule", rule_id, {"reason": reason})


def rules_in_force(conn: sqlite3.Connection, contract_id: int, boq_code: str, on_date: str) -> list[dict]:
    """For each rule code, the approved version in force on a date (old versions apply to old work)."""
    cands = rows(conn, """SELECT * FROM rules WHERE contract_id = ? AND boq_code = ?
                          AND status IN ('approved', 'superseded') AND effective_from <= ?
                          ORDER BY rule_code, effective_from DESC, version DESC""",
                 (contract_id, boq_code, on_date[:10]))
    chosen: dict[str, dict] = {}
    for c in cands:
        chosen.setdefault(c["rule_code"], c)
    return list(chosen.values())


# ---------- lots and tests ----------

def create_lot(conn: sqlite3.Connection, ledger: Ledger, *, contract_id: int, actor: str, boq_code: str,
               layer: str, ch_from: float, ch_to: float, placed_on: str, quantity: float,
               width_m: float | None = None, lot_size: float | None = None) -> int:
    if ch_to < ch_from:
        raise ValueError("Chainage 'to' must not be before 'from'")
    if lot_size is None:
        if width_m is None:
            raise ValueError("Give the lot width or the lot size used for test frequency")
        lot_size = (ch_to - ch_from) * width_m
    lid = insert(conn, "lots", {
        "contract_id": contract_id, "boq_code": boq_code, "layer": layer, "ch_from": ch_from, "ch_to": ch_to,
        "width_m": width_m, "quantity": quantity, "lot_size": lot_size, "placed_on": placed_on, "status": "open",
    })
    ledger.append(actor, "lot.created", "lot", lid, {"boq_code": boq_code, "ch_from": ch_from, "ch_to": ch_to,
                                                     "lot_size": lot_size})
    return lid


def add_sample(conn: sqlite3.Connection, ledger: Ledger, *, lot_id: int, actor: str, tag_id: str, taken_at: str,
               chainage: float | None = None, gps_lat: float | None = None, gps_lon: float | None = None,
               photo_sha256: str | None = None) -> int:
    sid = insert(conn, "samples", {"lot_id": lot_id, "tag_id": tag_id, "taken_at": taken_at, "chainage": chainage,
                                   "gps_lat": gps_lat, "gps_lon": gps_lon, "taken_by": actor,
                                   "photo_sha256": photo_sha256})
    ledger.append(actor, "sample.taken", "sample", sid, {"tag_id": tag_id, "lot_id": lot_id, "chainage": chainage,
                                                         "gps": [gps_lat, gps_lon], "taken_at": taken_at})
    return sid


def add_test(conn: sqlite3.Connection, ledger: Ledger, *, lot_id: int, actor: str, parameter: str, value: float,
             tested_on: str, performed_by: str = "contractor_qc", unit: str = "", chainage: float | None = None,
             sample_id: int | None = None, group_ref: str | None = None, lab: str = "",
             document_id: int | None = None) -> int:
    if performed_by not in ("contractor_qc", "consultant", "independent"):
        raise ValueError("performed_by must be contractor_qc, consultant or independent")
    tid = insert(conn, "tests", {
        "lot_id": lot_id, "sample_id": sample_id, "parameter": parameter, "value": value, "unit": unit,
        "group_ref": group_ref, "tested_on": tested_on, "chainage": chainage, "lab": lab,
        "performed_by": performed_by, "document_id": document_id, "entered_by": actor, "created_at": now_iso(),
    })
    ledger.append(actor, "test.entered", "test", tid, {"lot_id": lot_id, "parameter": parameter, "value": value,
                                                       "performed_by": performed_by, "document_id": document_id})
    lot = row(conn, "SELECT status FROM lots WHERE id = ?", (lot_id,))
    if lot and lot["status"] != "approved":
        update(conn, "lots", lot_id, {"status": "open"})
    return tid


def _tests_for(conn: sqlite3.Connection, lot_id: int) -> list[TestResult]:
    return [TestResult(t["id"], t["parameter"], t["value"], t["chainage"], t["group_ref"], t["tested_on"])
            for t in rows(conn, "SELECT * FROM tests WHERE lot_id = ? ORDER BY tested_on, id", (lot_id,))]


def evaluate_lot(conn: sqlite3.Connection, ledger: Ledger, lot_id: int, actor: str) -> dict:
    lot = row(conn, "SELECT * FROM lots WHERE id = ?", (lot_id,))
    if not lot:
        raise ValueError("Lot not found")
    rule_rows = rules_in_force(conn, lot["contract_id"], lot["boq_code"], lot["placed_on"])
    if not rule_rows:
        raise ValueError(f"No approved rules for BOQ item {lot['boq_code']} on {lot['placed_on']}")
    tests = _tests_for(conn, lot_id)
    findings = []
    for rr in rule_rows:
        findings.extend(evaluate_rule(Rule.from_row(rr), tests, lot["lot_size"]))
    result = overall(findings)
    fdicts = [f.to_dict() for f in findings]
    insert(conn, "evaluations", {"lot_id": lot_id, "result": result, "findings_json": json.dumps(fdicts),
                                 "evaluated_at": now_iso()})
    if lot["status"] != "approved":
        update(conn, "lots", lot_id, {"status": {PASS: "passed", MARGINAL: "marginal", FAIL: "failed"}[result]})
    new_ncrs = []
    for f in findings:
        if f.result != FAIL:
            continue
        exists = row(conn, """SELECT id FROM ncrs WHERE lot_id = ? AND rule_code = ? AND finding_kind = ?
                              AND IFNULL(chainage, -1) = IFNULL(?, -1) AND status = 'open'""",
                     (lot_id, f.rule_code, f.kind, f.chainage))
        if exists:
            continue
        nid = insert(conn, "ncrs", {
            "contract_id": lot["contract_id"], "lot_id": lot_id, "rule_code": f.rule_code, "finding_kind": f.kind,
            "description": f"{lot['boq_code']} {lot['layer'] or ''} ch {lot['ch_from']:g}-{lot['ch_to']:g}: {f.message}",
            "deviation": f.deviation, "chainage": f.chainage, "status": "open", "raised_at": now_iso(),
        })
        new_ncrs.append(nid)
        ledger.append(actor, "ncr.raised", "ncr", nid, {"lot_id": lot_id, "rule_code": f.rule_code,
                                                        "kind": f.kind, "deviation": f.deviation})
    ledger.append(actor, "lot.evaluated", "lot", lot_id, {"result": result, "rules": [
        f"{r['rule_code']} v{r['version']}" for r in rule_rows], "findings": len(findings)})
    return {"result": result, "findings": fdicts, "new_ncrs": new_ncrs}


def release_lot(conn: sqlite3.Connection, ledger: Ledger, lot_id: int, actor: str, role: str, note: str = "") -> None:
    """Release the hold point. Only for a lot that passed (or marginal with a note) and has no open NCRs."""
    require_role(role, "release_lot")
    lot = row(conn, "SELECT * FROM lots WHERE id = ?", (lot_id,))
    if not lot:
        raise ValueError("Lot not found")
    if lot["status"] not in ("passed", "marginal"):
        raise ValueError(f"Lot is '{lot['status']}'. Evaluate it and clear failures before release.")
    if lot["status"] == "marginal" and not note.strip():
        raise ValueError("A marginal lot needs a written note before release")
    open_ncrs = row(conn, "SELECT COUNT(*) AS n FROM ncrs WHERE lot_id = ? AND status = 'open'", (lot_id,))["n"]
    if open_ncrs:
        raise ValueError(f"{open_ncrs} open NCR(s) on this lot")
    update(conn, "lots", lot_id, {"status": "approved", "released_by": actor, "released_at": now_iso()})
    ledger.append(actor, "lot.released", "lot", lot_id, {"note": note})


def close_ncr(conn: sqlite3.Connection, ledger: Ledger, ncr_id: int, actor: str, role: str,
              disposition: str, reason: str) -> None:
    require_role(role, "close_ncr")
    if disposition not in ("rework", "retest", "accept_with_reason"):
        raise ValueError("Disposition must be rework, retest or accept_with_reason")
    if not reason.strip():
        raise ValueError("Every disposition needs a written reason")
    n = row(conn, "SELECT * FROM ncrs WHERE id = ?", (ncr_id,))
    if not n or n["status"] != "open":
        raise ValueError("NCR is not open")
    update(conn, "ncrs", ncr_id, {"status": "closed", "disposition": disposition, "reason": reason,
                                  "closed_by": actor, "closed_at": now_iso()})
    if disposition in ("rework", "retest") and n["lot_id"]:
        update(conn, "lots", n["lot_id"], {"status": "open"})
    elif disposition == "accept_with_reason" and n["lot_id"]:
        remaining = row(conn, "SELECT COUNT(*) AS n FROM ncrs WHERE lot_id = ? AND status = 'open'", (n["lot_id"],))["n"]
        lot = row(conn, "SELECT status FROM lots WHERE id = ?", (n["lot_id"],))
        if remaining == 0 and lot["status"] == "failed":
            # Every failure accepted with a reason: the engineer may now release it as marginal.
            update(conn, "lots", n["lot_id"], {"status": "marginal"})
    ledger.append(actor, "ncr.closed", "ncr", ncr_id, {"disposition": disposition, "reason": reason})


def latest_evaluation(conn: sqlite3.Connection, lot_id: int) -> dict | None:
    e = row(conn, "SELECT * FROM evaluations WHERE lot_id = ? ORDER BY id DESC LIMIT 1", (lot_id,))
    if e:
        e["findings"] = json.loads(e["findings_json"])
    return e
