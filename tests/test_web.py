"""Smoke-test every page and the main decisions through the web app."""
import os
import stat

import pytest
from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VBC_DATA_DIR", str(tmp_path / "var"))
    app = create_app(load_settings())
    from app.demo import seed
    seed(app.state.conn)
    with TestClient(app) as c:
        yield c
    for p in (tmp_path / "var").rglob("*"):
        if p.is_file():
            os.chmod(p, stat.S_IWUSR | stat.S_IRUSR)


def as_role(c, role):
    c.cookies.set("role", role)


@pytest.mark.parametrize("path", ["/", "/rules", "/standards", "/lots", "/lots/2", "/ncrs", "/documents", "/materials",
                                  "/ipcs", "/ipcs/2", "/ipcs/2/pack", "/ipcs/2/pack.csv", "/reports/monthly?month=2026-10",
                                  "/ledger"])
def test_pages_render(client, path):
    r = client.get(path)
    assert r.status_code == 200, r.text[:500]


def test_failed_lot_shows_deviation(client):
    r = client.get("/lots/2")
    assert "97.95" in r.text and "-0.2" in r.text


def test_quantity_surveyor_cannot_certify(client):
    as_role(client, "quantity_surveyor")
    r = client.post("/ipcs/2/certify", follow_redirects=True)
    assert "Only Resident Engineer" in r.text


def test_upload_and_manual_confirm(client):
    as_role(client, "inspector")
    r = client.post("/documents", files={"file": ("lab.txt", b"Field density BL-1204 96.8", "text/plain")},
                    data={"kind": "lab_report"}, follow_redirects=True)
    assert r.status_code == 200
    doc_id = int(str(r.url).rstrip("/").split("/")[-1].split("?")[0])
    r = client.post(f"/documents/{doc_id}/confirm", data={
        "lot_id": "2", "tested_on": "2026-10-12", "performed_by": "consultant",
        "param_0": "field_density_pct_mdd", "value_0": "98.7", "unit_0": "%", "keep_0": "on", "ch_0": "12+210"},
        follow_redirects=True)
    assert "Confirmed 1 result" in r.text


def test_astm_standard_upload_blocked(client):
    as_role(client, "materials_engineer")
    r = client.post("/documents", files={"file": ("d1557.pdf", b"%PDF", "application/pdf")},
                    data={"kind": "standard", "publisher": "ASTM"}, follow_redirects=True)
    assert "No active ASTM licence" in r.text


def test_whatsapp_rejects_unsigned(client):
    assert client.post("/intake/whatsapp", content=b"{}").status_code == 403
