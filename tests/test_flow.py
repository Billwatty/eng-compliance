"""End-to-end: quality decides what can be paid; people decide what is paid."""
import json

import pytest

from app import ipc, materials, qc, reports
from app.roles import NotAllowed


def lines(conn, number):
    return [dict(r) for r in conn.execute(
        "SELECT l.* FROM ipc_lines l JOIN ipcs i ON i.id = l.ipc_id WHERE i.number = ? ORDER BY l.id", (number,))]


def test_demo_ipc2_findings(conn, demo):
    l = lines(conn, 2)
    checks = [{f["check"] for f in json.loads(x["findings_json"])} for x in l]
    assert checks[0] >= {"qc_coverage", "open_ncr"}      # failed lot 12+000-12+500
    assert checks[1] == {"all"}                            # released neighbour lot, boundary not shared
    assert checks[2] == {"duplicate"}                      # subbase already certified in IPC 1
    assert checks[3] == {"consumption"}                    # culvert cement short by 9.5%
    assert [x["status"] for x in l] == ["exception", "complete", "exception", "exception"]


def test_worked_example_ncrs(conn, demo):
    ncrs = [dict(r) for r in conn.execute("SELECT * FROM ncrs WHERE lot_id = 2 ORDER BY id")]
    assert {(n["finding_kind"], n["deviation"]) for n in ncrs} == {("single", -0.2), ("mean", -0.05), ("frequency", -2)}


def test_cement_variance(conn, demo):
    v = materials.consumption_variance(conn, demo, "8.3")[0]
    assert v["expected"] == 840 and v["issued"] == 760 and v["variance_pct"] == -9.52 and v["result"] == "fail"


def test_material_checks(conn, demo):
    m1 = {c.ref: c.result for c in materials.check_orders(conn, demo)}
    assert m1 == {"PO-114": "pass", "PO-121": "pass", "PO-127": "fail"}
    m2 = {c.ref: c for c in materials.check_deliveries(conn, demo)}
    assert m2["WB-5530"].result == "pass"
    assert m2["WB-5544"].result == "fail" and "H7790" in m2["WB-5544"].message and "GSA" in m2["WB-5544"].message
    m3 = materials.store_balances(conn, demo)[0]
    assert m3["book"] == 240 and m3["difference"] == -2


def test_roles_and_overrides(conn, ledger, demo):
    i2 = conn.execute("SELECT id FROM ipcs WHERE number = 2").fetchone()["id"]
    l = lines(conn, 2)
    with pytest.raises(NotAllowed):
        ipc.certify_ipc(conn, ledger, i2, "QS", "quantity_surveyor")
    with pytest.raises(ValueError, match="written reason"):
        ipc.review_line(conn, ledger, l[3]["id"], "QS", "quantity_surveyor", "accept")
    ipc.review_line(conn, ledger, l[0]["id"], "QS", "quantity_surveyor", "hold")
    ipc.review_line(conn, ledger, l[1]["id"], "QS", "quantity_surveyor", "accept")
    ipc.review_line(conn, ledger, l[2]["id"], "QS", "quantity_surveyor", "hold", "duplicate of IPC 1")
    ipc.review_line(conn, ledger, l[3]["id"], "RE", "resident_engineer", "accept",
                    "Cubes passed at 41-43 MPa; store count investigated")
    out = ipc.certify_ipc(conn, ledger, i2, "RE", "resident_engineer")
    assert out == {"certified": 2, "held": 2}
    pack = ipc.evidence_pack(conn, i2)
    assert pack["payable"] == 525 * 260 + 120 * 2400 and pack["held"] == 525 * 260 + 262.5 * 180
    overrides = [json.loads(r["payload_json"]) for r in conn.execute(
        "SELECT payload_json FROM ledger WHERE action = 'ipc.line_reviewed'")]
    assert any(o["override"] for o in overrides)
    assert ledger.verify_chain().ok


def test_rework_then_pass(conn, ledger, demo):
    for n in conn.execute("SELECT id FROM ncrs WHERE lot_id = 2 AND status = 'open'").fetchall():
        qc.close_ncr(conn, ledger, n["id"], "ME", "materials_engineer", "rework", "Recompact around 12+210")
    for v, ch in [(98.6, 12210), (98.4, 12250), (98.9, 12290)]:
        qc.add_test(conn, ledger, lot_id=2, actor="CQC", parameter="field_density_pct_mdd", value=v,
                    tested_on="2026-10-12", chainage=ch)
    conn.execute("DELETE FROM tests WHERE lot_id = 2 AND value = 96.8")
    out = qc.evaluate_lot(conn, ledger, 2, "ME")
    # 97.2 sits within the 0.5-point marginal band, so the lot passes as marginal.
    assert out["result"] == "marginal", [f for f in out["findings"] if f["result"] == "fail"]
    with pytest.raises(NotAllowed):
        qc.release_lot(conn, ledger, 2, "QS", "quantity_surveyor")
    with pytest.raises(ValueError, match="written note"):
        qc.release_lot(conn, ledger, 2, "RE", "resident_engineer")
    qc.release_lot(conn, ledger, 2, "RE", "resident_engineer", "97.2 at 12+450 accepted; mean 98.3")
    assert conn.execute("SELECT status FROM lots WHERE id = 2").fetchone()["status"] == "approved"


def test_rule_versions_apply_by_date(conn, ledger, demo):
    rid = qc.add_rule(conn, ledger, contract_id=demo, actor="ME", rule_code="BASE-DENSITY-01", boq_code="4.2",
                      parameter="field_density_pct_mdd", limit_type="min_and_mean", params={"min": 98, "mean_min": 99},
                      source_publisher="CONTRACT", source_ref="Engineer's instruction EI-12", effective_from="2026-11-01",
                      frequency_qty=350)
    qc.approve_rule(conn, ledger, rid, "RE", "resident_engineer")
    old = qc.rules_in_force(conn, demo, "4.2", "2026-10-06")
    new = qc.rules_in_force(conn, demo, "4.2", "2026-11-05")
    v_old = {r["rule_code"]: r["version"] for r in old}["BASE-DENSITY-01"]
    v_new = {r["rule_code"]: r["version"] for r in new}["BASE-DENSITY-01"]
    assert (v_old, v_new) == (1, 2)


def test_monthly_report(conn, demo):
    rep = reports.monthly_quality_report(conn, demo, "2026-10")
    dens = [l for l in rep["lines"] if l["parameter"] == "field_density_pct_mdd"][0]
    assert dens["required"] == 20 and dens["done"] == 18
    assert dens["verification_pct"] > 0
