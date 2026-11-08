import pytest

from app import licences
from app.intake import store_document


def test_ledger_detects_tampering(conn, ledger):
    for i in range(5):
        ledger.append("tester", "thing.done", "thing", i, {"n": i})
    assert ledger.verify_chain().ok
    conn.execute("DROP TRIGGER ledger_no_update")  # simulate someone editing the database directly
    conn.execute("UPDATE ledger SET payload_json = '{\"n\":99}' WHERE id = 3")
    rep = ledger.verify_chain()
    assert not rep.ok and rep.first_bad_id == 3


def test_ledger_is_append_only(conn, ledger):
    ledger.append("tester", "x", "y")
    with pytest.raises(Exception):
        conn.execute("DELETE FROM ledger")


def test_vault_is_write_once(vault):
    d = vault.put(b"lab report")
    assert vault.put(b"lab report") == d
    assert vault.get(d) == b"lab report"
    path = vault.path_for(d)
    import os, stat
    os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
    path.write_bytes(b"altered")
    with pytest.raises(RuntimeError):
        vault.get(d)


def test_licence_gate(conn, ledger, vault, demo):
    assert licences.is_permitted(conn, "MRH", "ai_extract")
    assert not licences.is_permitted(conn, "ASTM", "ai_extract")
    with pytest.raises(licences.LicenceDenied):
        store_document(conn, vault, ledger, contract_id=demo, actor="t", data=b"%PDF", filename="d1557.pdf",
                       kind="standard", publisher="ASTM")
    licences.add_licence(conn, "GSA", "Demo Consulting", ["store", "ai_extract"], expires_on="2099-01-01")
    assert licences.is_permitted(conn, "GSA", "ai_extract")
    licences.add_licence(conn, "ISO", "Demo Consulting", ["store", "ai_extract"], expires_on="2020-01-01")
    assert not licences.is_permitted(conn, "ISO", "ai_extract"), "expired licence must not count"


def test_ai_rule_needs_licence(conn, ledger, demo):
    from app import qc
    with pytest.raises(licences.LicenceDenied):
        qc.add_rule(conn, ledger, contract_id=demo, actor="AI", rule_code="X", boq_code="4.2", parameter="p",
                    limit_type="min", params={"min": 1}, source_publisher="ASTM", source_ref="D1557 7.1",
                    effective_from="2026-01-01", drafted_by="ai")
    rid = qc.add_rule(conn, ledger, contract_id=demo, actor="ME", rule_code="X", boq_code="4.2", parameter="p",
                      limit_type="min", params={"min": 1}, source_publisher="ASTM", source_ref="D1557 7.1",
                      source_quote="should be dropped", effective_from="2026-01-01")
    r = conn.execute("SELECT source_quote FROM rules WHERE id = ?", (rid,)).fetchone()
    assert r["source_quote"] == "", "no excerpt may be stored without a store_excerpt licence"
