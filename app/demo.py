"""Demo contract built from the worked examples in docs/architecture.html.

All figures are illustrative. Specification limits marked 'verify' come from
unofficial copies of the 2006-07 Ghana Standard Specification.
"""
from __future__ import annotations

import sqlite3

from . import ipc, qc
from .db import insert
from .ledger import Ledger

RE = ("A. Mensah (RE)", "resident_engineer")
ME = ("E. Owusu (Materials)", "materials_engineer")
QS = ("K. Boateng (QS)", "quantity_surveyor")
CQC = "Contractor QC"

GRADING_BANDS = {"37.5": [100, 100], "28": [80, 100], "20": [60, 85], "10": [40, 65], "5": [30, 50],
                 "2": [20, 40], "0.425": [10, 25], "0.075": [5, 15]}
GOOD_GRADING = {"37.5": 100, "28": 92, "20": 74, "10": 52, "5": 41, "2": 29, "0.425": 17, "0.075": 9}


def seed(conn: sqlite3.Connection) -> int:
    ledger = Ledger(conn)
    k = insert(conn, "contracts", {
        "name": "Demo: feeder road rehabilitation, Lot 2B (illustrative data)",
        "employer": "Ghana Highway Authority (demo)", "consultant": "Demo Consulting Engineers",
        "contractor": "Demo Roads Ltd", "currency": "GHS"})
    ledger.append("setup", "contract.created", "contract", k, {"demo": True})

    for code, desc, unit, qty, rate in [
        ("4.1", "Natural gravel subbase G30, 175 mm", "m3", 6125, 180),
        ("4.2", "Natural gravel base G60, 150 mm", "m3", 5250, 260),
        ("6.1", "Asphalt concrete wearing course, 50 mm", "m2", 35000, 95),
        ("8.3", "Class C30/37 concrete in culverts", "m3", 600, 2400),
        ("8.5", "High-yield reinforcement B500", "t", 60, 14000),
    ]:
        insert(conn, "boq_items", {"contract_id": k, "code": code, "description": desc, "unit": unit,
                                   "quantity": qty, "rate": rate})

    eff = "2026-01-15"
    rule_ids = [
        qc.add_rule(conn, ledger, contract_id=k, actor=ME[0], rule_code="BASE-DENSITY-01", boq_code="4.2",
                    parameter="field_density_pct_mdd", unit="% MDD", method="GHA S1", limit_type="min_and_mean",
                    params={"min": 97, "mean_min": 98}, frequency_qty=350, marginal_band=0.5,
                    source_publisher="MRH", source_ref="Standard Specification Table 12.2 (2006 draft, verify)",
                    effective_from=eff),
        qc.add_rule(conn, ledger, contract_id=k, actor=ME[0], rule_code="BASE-LEVEL-01", boq_code="4.2",
                    parameter="level_deviation_mm", unit="mm", method="levels on 10 m grid", limit_type="tolerance",
                    params={"design": 0, "plus": 0, "minus": 25}, source_publisher="MRH",
                    source_ref="Standard Specification Section 3 tolerances (2007 draft, units assumed mm, verify)",
                    effective_from=eff),
        qc.add_rule(conn, ledger, contract_id=k, actor=ME[0], rule_code="BASE-GRADING-01", boq_code="4.2",
                    parameter="grading", unit="% passing", method="wet sieve", limit_type="envelope",
                    params={"sieves": GRADING_BANDS}, frequency_qty=3500, source_publisher="MRH",
                    source_ref="G60 grading envelope (illustrative bands, verify)", effective_from=eff),
        qc.add_rule(conn, ledger, contract_id=k, actor=ME[0], rule_code="SUBBASE-DENSITY-01", boq_code="4.1",
                    parameter="field_density_pct_mdd", unit="% MDD", method="GHA S1", limit_type="min_and_mean",
                    params={"min": 94, "mean_min": 95}, frequency_qty=350, marginal_band=0.5,
                    source_publisher="MRH", source_ref="Standard Specification Table 12.2 (2006 draft, verify)",
                    effective_from=eff),
        qc.add_rule(conn, ledger, contract_id=k, actor=ME[0], rule_code="CULVERT-CUBE-01", boq_code="8.3",
                    parameter="cube_strength_mpa", unit="MPa", method="BS EN 12390-3", limit_type="concrete_cube",
                    params={"fck_cube": 37, "mean_margin": 4, "individual_margin": 4, "group_size": 3},
                    frequency_qty=50, source_publisher="BSI",
                    source_ref="BS EN 206 conformity, initial production (limits entered by hand, verify)",
                    effective_from=eff),
    ]
    for rid in rule_ids:
        qc.approve_rule(conn, ledger, rid, *RE)
    qc.add_rule(conn, ledger, contract_id=k, actor=ME[0], rule_code="ASPHALT-CORE-01", boq_code="6.1",
                parameter="core_density_pct", unit="% Marshall", method="cores", limit_type="min",
                params={"min": 97}, frequency_qty=500, source_publisher="MRH",
                source_ref="Asphalt compaction clause (to be checked against the contract edition)", effective_from=eff)

    # Subbase lot, fully tested and released (paid in IPC 1).
    l3 = qc.create_lot(conn, ledger, contract_id=k, actor=CQC, boq_code="4.1", layer="Subbase", ch_from=12000,
                       ch_to=13000, width_m=7.5, quantity=1312.5, placed_on="2026-09-20")
    for i in range(22):
        qc.add_test(conn, ledger, lot_id=l3, actor=CQC, parameter="field_density_pct_mdd",
                    value=[95.4, 96.1, 95.8, 96.6, 95.2][i % 5], tested_on="2026-09-22", chainage=12000 + i * 45)
    qc.evaluate_lot(conn, ledger, l3, CQC)
    qc.release_lot(conn, ledger, l3, *RE)

    # Worked example: base lot 12+000 to 12+500 with 8 of 10 tests.
    l1 = qc.create_lot(conn, ledger, contract_id=k, actor=CQC, boq_code="4.2", layer="Base", ch_from=12000,
                       ch_to=12500, width_m=7, quantity=525, placed_on="2026-10-06")
    for i, v in enumerate([98.4, 97.6, 99.1, 96.8, 98.0, 97.9, 98.6, 97.2]):
        sid = qc.add_sample(conn, ledger, lot_id=l1, actor=CQC, tag_id=f"BL-12{i + 1:02d}",
                            taken_at=f"2026-10-07T0{8 + i // 4}:{(i % 4) * 15:02d}", chainage=12030 + i * 60,
                            gps_lat=7.0412, gps_lon=0.4621)
        qc.add_test(conn, ledger, lot_id=l1, actor=CQC, parameter="field_density_pct_mdd", value=v,
                    tested_on="2026-10-08", chainage=12030 + i * 60, sample_id=sid)
    for lot_id, ch0 in ((l1, 12000),):
        for s, v in GOOD_GRADING.items():
            qc.add_test(conn, ledger, lot_id=lot_id, actor=CQC, parameter=f"grading:{s}", value=v,
                        tested_on="2026-10-08", group_ref="G1")
        for j, dv in enumerate([-12, -8, -21, -5, -15]):
            qc.add_test(conn, ledger, lot_id=lot_id, actor=CQC, parameter="level_deviation_mm", value=dv,
                        tested_on="2026-10-08", chainage=ch0 + 50 + j * 100)
    qc.evaluate_lot(conn, ledger, l1, ME[0])

    # Neighbouring base lot that passes and is released.
    l2 = qc.create_lot(conn, ledger, contract_id=k, actor=CQC, boq_code="4.2", layer="Base", ch_from=12500,
                       ch_to=13000, width_m=7, quantity=525, placed_on="2026-10-09")
    for i, v in enumerate([98.9, 99.3, 98.2, 98.7, 99.0, 98.4, 97.9, 98.8, 99.1, 98.5]):
        qc.add_test(conn, ledger, lot_id=l2, actor=CQC if i % 4 else "Consultant lab",
                    performed_by="contractor_qc" if i % 4 else "consultant", parameter="field_density_pct_mdd",
                    value=v, tested_on="2026-10-10", chainage=12520 + i * 48)
    for s, v in GOOD_GRADING.items():
        qc.add_test(conn, ledger, lot_id=l2, actor=CQC, parameter=f"grading:{s}", value=v, tested_on="2026-10-10",
                    group_ref="G2")
    for j, dv in enumerate([-6, -11, -3, -17, -9]):
        qc.add_test(conn, ledger, lot_id=l2, actor=CQC, parameter="level_deviation_mm", value=dv,
                    tested_on="2026-10-10", chainage=12550 + j * 100)
    qc.evaluate_lot(conn, ledger, l2, ME[0])
    qc.release_lot(conn, ledger, l2, *RE)

    # Culvert pour: 120 m3 at 12+350, three cube sets that pass.
    l4 = qc.create_lot(conn, ledger, contract_id=k, actor=CQC, boq_code="8.3", layer="Culvert CV-07 barrel",
                       ch_from=12350, ch_to=12350, lot_size=120, quantity=120, placed_on="2026-09-28")
    for set_ref, vals in (("C1", (42, 43, 41)), ("C2", (44, 42, 43)), ("C3", (40, 41, 42))):
        for v in vals:
            qc.add_test(conn, ledger, lot_id=l4, actor=CQC, parameter="cube_strength_mpa", value=v,
                        tested_on="2026-10-26", group_ref=set_ref)
    qc.evaluate_lot(conn, ledger, l4, ME[0])
    qc.release_lot(conn, ledger, l4, *RE)

    # Materials chain.
    insert(conn, "approved_sources", {"contract_id": k, "material": "Cement", "supplier": "Demo Cement Co",
                                      "grade": "42.5N", "approved_by": RE[0], "approved_on": "2026-02-01"})
    insert(conn, "approved_sources", {"contract_id": k, "material": "Rebar", "supplier": "Demo Steel Mills",
                                      "grade": "B500", "approved_by": RE[0], "approved_on": "2026-02-01"})
    for po in [("PO-114", "Demo Cement Co", "Cement", "42.5N", 1000, "bag", "8.3"),
               ("PO-121", "Demo Steel Mills", "Rebar", "B500", 20, "t", "8.5"),
               ("PO-127", "Accra Steel Traders", "Rebar", "B500", 10, "t", "8.5")]:
        insert(conn, "purchase_orders", dict(zip(
            ["po_ref", "supplier", "material", "grade", "quantity", "unit", "boq_code"], po), contract_id=k))
    for d in [("WB-5521", "PO-114", "Demo Cement Co", "Cement", "42.5N", 600, "bag", None, None, 0, "2026-09-10"),
              ("WB-5530", "PO-121", "Demo Steel Mills", "Rebar", "B500", 12, "t", "H7731", "H7731", 1, "2026-09-12"),
              ("WB-5544", "PO-121", "Demo Steel Mills", "Rebar", "B500", 8, "t", "H7790", "H7739", 0, "2026-09-19"),
              ("WB-5561", "PO-114", "Demo Cement Co", "Cement", "42.5N", 400, "bag", None, None, 0, "2026-09-24")]:
        insert(conn, "deliveries", dict(zip(
            ["waybill_no", "po_ref", "supplier", "material", "grade", "quantity", "unit", "heat_no", "cert_heat_no",
             "gsa_marked", "delivered_on"], d), contract_id=k))
    for m in [("Cement", "in", 600, "bag", "2026-09-10", None, None, "GRN-201"),
              ("Cement", "in", 400, "bag", "2026-09-24", None, None, "GRN-214"),
              ("Cement", "out", 760, "bag", "2026-09-28", "8.3", 12350, "IV-0931"),
              ("Cement", "count", 238, "bag", "2026-10-31", None, None, "Monthly count")]:
        insert(conn, "store_moves", dict(zip(
            ["material", "direction", "quantity", "unit", "moved_on", "boq_code", "chainage", "ref"], m), contract_id=k))
    insert(conn, "consumption_rates", {"contract_id": k, "boq_code": "8.3", "material": "Cement",
                                       "rate_per_unit": 7, "material_unit": "bag", "allowance_pct": 3,
                                       "source": "Approved mix design MD-04: 350 kg/m3 = 7 bags of 50 kg"})

    # IPC 1: subbase, certified.
    i1 = ipc.create_ipc(conn, ledger, k, 1, "2026-09-30", QS[0])
    ipc.add_line(conn, ledger, i1, QS[0], "4.1", 1312.5, 12000, 13000, "Subbase ch 12+000 to 13+000")
    ipc.check_ipc(conn, ledger, i1, QS[0])
    for line in conn.execute("SELECT id FROM ipc_lines WHERE ipc_id = ?", (i1,)).fetchall():
        ipc.review_line(conn, ledger, line["id"], *QS, "accept", "Spot-checked against lot 1")
    ipc.certify_ipc(conn, ledger, i1, *RE)

    # IPC 2: this month's claim, checked and waiting for review.
    i2 = ipc.create_ipc(conn, ledger, k, 2, "2026-10-31", QS[0])
    for boq, qty, a, b, desc in [("4.2", 525, 12000, 12500, "Base ch 12+000 to 12+500"),
                                 ("4.2", 525, 12500, 13000, "Base ch 12+500 to 13+000"),
                                 ("4.1", 262.5, 12800, 13000, "Subbase ch 12+800 to 13+000"),
                                 ("8.3", 120, 12350, 12350, "Culvert CV-07 barrel")]:
        ipc.add_line(conn, ledger, i2, QS[0], boq, qty, a, b, desc)
    ipc.check_ipc(conn, ledger, i2, QS[0])
    conn.commit()
    return k
