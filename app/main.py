"""Web app: FastAPI routes over the compliance engine."""
from __future__ import annotations

import csv
import io
import json
import threading
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from . import extraction, intake, ipc, licences, materials, qc, reports
from .config import Settings, load_settings
from .db import connect, insert, row, rows, update
from .ledger import FileVault, Ledger
from .matcher import match_lab_report
from .roles import ROLES, NotAllowed, require_role

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
TEMPLATES.env.filters["ch"] = lambda m: "" if m is None else f"{int(m) // 1000}+{int(round(m)) % 1000:03d}"
TEMPLATES.env.filters["num"] = lambda x, d=2: "" if x is None else (f"{x:,.{d}f}".rstrip("0").rstrip(".") if isinstance(x, float) else f"{x:,}")
TEMPLATES.env.filters["fromjson"] = lambda s: json.loads(s) if s else None

USER_ERRORS = (ValueError, NotAllowed, licences.LicenceDenied, extraction.ExtractionUnavailable,
               extraction.ExtractionRefused, extraction.ExtractionFailed)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Verify Before Certify")
    conn = connect(settings.db_path)
    app.state.settings = settings
    app.state.conn = conn
    app.state.vault = FileVault(settings.vault_dir)
    app.state.ledger = Ledger(conn)
    app.state.lock = threading.Lock()

    # ---------- helpers ----------

    def who(request: Request) -> tuple[str, str]:
        role = request.cookies.get("role", "inspector")
        if role not in ROLES:
            role = "inspector"
        name = request.cookies.get("name") or ROLES[role]
        return name, role

    def contract() -> dict | None:
        return row(conn, "SELECT * FROM contracts ORDER BY id LIMIT 1")

    def cid() -> int:
        c = contract()
        if not c:
            raise HTTPException(409, "Set up the contract first")
        return c["id"]

    @contextmanager
    def tx():
        with app.state.lock:
            try:
                yield conn, app.state.ledger
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def back(path: str, msg: str = "", error: bool = False) -> RedirectResponse:
        sep = "&" if "?" in path else "?"
        url = path + (f"{sep}msg={quote(msg)}" + ("&err=1" if error else "") if msg else "")
        return RedirectResponse(url, status_code=303)

    def act(path: str, fn, ok_msg: str):
        try:
            with tx():
                out = fn()
            return back(path, ok_msg if not callable(ok_msg) else ok_msg(out))
        except USER_ERRORS as e:
            return back(path, str(e), True)

    def page(request: Request, name: str, **ctx):
        actor, role = who(request)
        ctx.update(request=request, actor=actor, role=role, roles=ROLES, contract=contract(),
                   msg=request.query_params.get("msg"), err=request.query_params.get("err"),
                   today=date.today().isoformat())
        return TEMPLATES.TemplateResponse(request, name, ctx)

    def fnum(v: str | None) -> float | None:
        v = (v or "").strip().replace(",", "")
        if not v:
            return None
        if "+" in v:  # chainage 12+350
            km, m = v.split("+", 1)
            return float(km) * 1000 + float(m)
        return float(v)

    # ---------- session ----------

    @app.post("/session")
    def set_session(request: Request, role: str = Form(...), name: str = Form(""), next: str = Form("/")):
        resp = RedirectResponse(next or "/", status_code=303)
        resp.set_cookie("role", role if role in ROLES else "inspector", samesite="lax")
        resp.set_cookie("name", name.strip(), samesite="lax")
        return resp

    # ---------- overview ----------

    @app.get("/", response_class=HTMLResponse)
    def overview(request: Request):
        c = contract()
        if not c:
            return page(request, "setup.html")
        k = c["id"]
        stats = {
            "rules_draft": row(conn, "SELECT COUNT(*) n FROM rules WHERE contract_id=? AND status='draft'", (k,))["n"],
            "rules_live": row(conn, "SELECT COUNT(*) n FROM rules WHERE contract_id=? AND status='approved'", (k,))["n"],
            "lots": rows(conn, "SELECT status, COUNT(*) n FROM lots WHERE contract_id=? GROUP BY status", (k,)),
            "ncrs_open": row(conn, "SELECT COUNT(*) n FROM ncrs WHERE contract_id=? AND status='open'", (k,))["n"],
            "docs_waiting": row(conn, "SELECT COUNT(*) n FROM documents WHERE contract_id=? AND status IN ('received','extracted')", (k,))["n"],
            "ipcs": rows(conn, "SELECT * FROM ipcs WHERE contract_id=? ORDER BY number DESC LIMIT 3", (k,)),
        }
        chain = app.state.ledger.verify_chain()
        return page(request, "overview.html", stats=stats, chain=chain)

    @app.post("/contract")
    def create_contract(name: str = Form(...), employer: str = Form(""), consultant: str = Form(""),
                        contractor: str = Form("")):
        def go():
            k = insert(conn, "contracts", {"name": name, "employer": employer, "consultant": consultant,
                                           "contractor": contractor})
            app.state.ledger.append("setup", "contract.created", "contract", k, {"name": name})
        return act("/", go, "Contract created")

    # ---------- BOQ and rules ----------

    @app.get("/rules", response_class=HTMLResponse)
    def rules_page(request: Request):
        k = cid()
        boq = rows(conn, "SELECT * FROM boq_items WHERE contract_id=? ORDER BY code", (k,))
        rl = rows(conn, "SELECT * FROM rules WHERE contract_id=? ORDER BY status='draft' DESC, rule_code, version DESC", (k,))
        for r in rl:
            r["params"] = json.loads(r["params_json"])
        specs = rows(conn, "SELECT * FROM documents WHERE contract_id=? AND kind IN ('spec','standard') ORDER BY id DESC", (k,))
        return page(request, "rules.html", boq=boq, rules=rl, specs=specs, licence_status=licences.register_status(conn))

    @app.post("/boq/upload")
    async def boq_upload(request: Request, file: UploadFile = File(...)):
        data = await file.read()
        def go():
            k = cid()
            if file.filename.lower().endswith(".xlsx"):
                import openpyxl
                ws = openpyxl.load_workbook(io.BytesIO(data), read_only=True).active
                it = ws.iter_rows(values_only=True)
                header = [str(h).strip().lower() for h in next(it)]
                recs = [dict(zip(header, r)) for r in it]
            else:
                recs = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
                recs = [{(kk or "").strip().lower(): v for kk, v in r.items()} for r in recs]
            n = 0
            for r in recs:
                if not r.get("code"):
                    continue
                conn.execute("""INSERT INTO boq_items (contract_id, code, description, unit, quantity, rate, material)
                                VALUES (?,?,?,?,?,?,?) ON CONFLICT(contract_id, code) DO UPDATE SET
                                description=excluded.description, unit=excluded.unit, quantity=excluded.quantity,
                                rate=excluded.rate, material=excluded.material""",
                             (k, str(r["code"]).strip(), r.get("description") or "", r.get("unit") or "",
                              float(r.get("quantity") or 0), float(r["rate"]) if r.get("rate") not in (None, "") else None,
                              r.get("material") or None))
                n += 1
            app.state.ledger.append(who(request)[0], "boq.imported", "contract", k, {"items": n, "file": file.filename})
            return n
        return act("/rules", go, lambda n: f"Imported {n} BOQ items")

    @app.post("/rules")
    def rule_add(request: Request, rule_code: str = Form(...), boq_code: str = Form(...), parameter: str = Form(...),
                 limit_type: str = Form(...), params_json: str = Form(...), unit: str = Form(""),
                 method: str = Form(""), frequency_qty: str = Form(""), marginal_band: str = Form("0"),
                 source_publisher: str = Form(...), source_ref: str = Form(...), effective_from: str = Form(...)):
        actor, role = who(request)
        def go():
            require_role(role, "enter_data")
            try:
                params = json.loads(params_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"Limit values are not valid JSON: {e.msg}") from e
            return qc.add_rule(conn, app.state.ledger, contract_id=cid(), actor=actor, rule_code=rule_code.strip(),
                               boq_code=boq_code.strip(), parameter=parameter.strip(), limit_type=limit_type,
                               params=params, unit=unit, method=method, frequency_qty=fnum(frequency_qty),
                               marginal_band=fnum(marginal_band) or 0.0, source_publisher=source_publisher,
                               source_ref=source_ref, effective_from=effective_from, drafted_by="manual")
        return act("/rules", go, "Rule drafted. An engineer must approve it before it is used.")

    @app.post("/rules/{rule_id}/approve")
    def rule_approve(request: Request, rule_id: int):
        actor, role = who(request)
        return act("/rules", lambda: qc.approve_rule(conn, app.state.ledger, rule_id, actor, role), "Rule approved")

    @app.post("/rules/{rule_id}/reject")
    def rule_reject(request: Request, rule_id: int, reason: str = Form("")):
        actor, role = who(request)
        return act("/rules", lambda: qc.reject_rule(conn, app.state.ledger, rule_id, actor, role, reason), "Rule rejected")

    @app.post("/rules/draft")
    def rule_draft_ai(request: Request, document_id: int = Form(...), effective_from: str = Form(...)):
        actor, role = who(request)
        try:
            require_role(role, "enter_data")
            doc = row(conn, "SELECT * FROM documents WHERE id = ?", (document_id,))
            if not doc:
                raise ValueError("Document not found")
            publisher = doc["publisher"] or "CONTRACT"
            licences.require(conn, publisher, "ai_extract")
            boq = rows(conn, "SELECT * FROM boq_items WHERE contract_id=?", (cid(),))
            drafts = extraction.draft_rules(settings, app.state.vault.get(doc["sha256"]), doc["filename"], doc["mime"], boq)
        except USER_ERRORS as e:
            return back("/rules", str(e), True)
        made, skipped = 0, []
        with tx():
            for d in drafts.rules:
                try:
                    qc.add_rule(conn, app.state.ledger, contract_id=cid(), actor=f"AI draft for {actor}",
                                rule_code=d.rule_code, boq_code=d.boq_code, parameter=d.parameter,
                                limit_type=d.limit_type, params=d.params(), unit=d.unit, method=d.method or "",
                                frequency_qty=d.frequency_qty, source_publisher=publisher,
                                source_ref=f"{doc['filename']}: {d.source_ref}", source_quote=d.source_quote or "",
                                effective_from=effective_from, drafted_by="ai")
                    made += 1
                except ValueError as e:
                    skipped.append(f"{d.rule_code}: {e}")
        msg = f"AI drafted {made} rule(s) for approval."
        if skipped:
            msg += f" Skipped {len(skipped)} incomplete draft(s): " + "; ".join(skipped[:3])
        return back("/rules", msg)

    # ---------- standards and licences ----------

    @app.get("/standards", response_class=HTMLResponse)
    def standards_page(request: Request):
        return page(request, "standards.html", status=licences.register_status(conn),
                    licences=rows(conn, "SELECT * FROM licences ORDER BY publisher, id"),
                    open_sources=sorted(licences.OPEN_SOURCES))

    @app.post("/licences")
    def licence_add(request: Request, publisher: str = Form(...), holder: str = Form(...),
                    uses: list[str] = Form(...), customers: str = Form(""), expires_on: str = Form(""),
                    reference: str = Form("")):
        actor, role = who(request)
        def go():
            require_role(role, "manage_licences")
            lid = licences.add_licence(conn, publisher, holder, uses, customers, expires_on or None, reference)
            app.state.ledger.append(actor, "licence.added", "licence", lid,
                                    {"publisher": publisher, "uses": uses, "expires_on": expires_on})
        return act("/standards", go, "Licence recorded")

    # ---------- lots, tests, NCRs ----------

    @app.get("/lots", response_class=HTMLResponse)
    def lots_page(request: Request):
        k = cid()
        lots = rows(conn, """SELECT l.*, (SELECT COUNT(*) FROM tests t WHERE t.lot_id=l.id) AS n_tests,
                             (SELECT COUNT(*) FROM ncrs n WHERE n.lot_id=l.id AND n.status='open') AS n_ncrs
                             FROM lots l WHERE contract_id=? ORDER BY boq_code, ch_from""", (k,))
        boq = rows(conn, "SELECT * FROM boq_items WHERE contract_id=? ORDER BY code", (k,))
        return page(request, "lots.html", lots=lots, boq=boq)

    @app.post("/lots")
    def lot_add(request: Request, boq_code: str = Form(...), layer: str = Form(""), ch_from: str = Form(...),
                ch_to: str = Form(...), width_m: str = Form(""), lot_size: str = Form(""), quantity: str = Form(...),
                placed_on: str = Form(...)):
        actor, role = who(request)
        def go():
            require_role(role, "enter_data")
            return qc.create_lot(conn, app.state.ledger, contract_id=cid(), actor=actor, boq_code=boq_code,
                                 layer=layer, ch_from=fnum(ch_from), ch_to=fnum(ch_to), width_m=fnum(width_m),
                                 lot_size=fnum(lot_size), quantity=fnum(quantity), placed_on=placed_on)
        try:
            with tx():
                lid = go()
            return back(f"/lots/{lid}", "Lot created. Add samples and results, then evaluate.")
        except USER_ERRORS as e:
            return back("/lots", str(e), True)

    @app.get("/lots/{lot_id}", response_class=HTMLResponse)
    def lot_page(request: Request, lot_id: int):
        lot = row(conn, "SELECT * FROM lots WHERE id=?", (lot_id,))
        if not lot:
            raise HTTPException(404)
        tests = rows(conn, """SELECT t.*, s.tag_id FROM tests t LEFT JOIN samples s ON s.id=t.sample_id
                              WHERE t.lot_id=? ORDER BY t.tested_on, t.id""", (lot_id,))
        samples = rows(conn, "SELECT * FROM samples WHERE lot_id=? ORDER BY id", (lot_id,))
        rules_live = qc.rules_in_force(conn, lot["contract_id"], lot["boq_code"], lot["placed_on"])
        for r in rules_live:
            r["params"] = json.loads(r["params_json"])
        ev = qc.latest_evaluation(conn, lot_id)
        ncrs = rows(conn, "SELECT * FROM ncrs WHERE lot_id=? ORDER BY id DESC", (lot_id,))
        return page(request, "lot.html", lot=lot, tests=tests, samples=samples, rules=rules_live, ev=ev, ncrs=ncrs)

    @app.post("/lots/{lot_id}/samples")
    def sample_add(request: Request, lot_id: int, tag_id: str = Form(...), taken_at: str = Form(...),
                   chainage: str = Form(""), gps_lat: str = Form(""), gps_lon: str = Form("")):
        actor, role = who(request)
        def go():
            require_role(role, "enter_data")
            qc.add_sample(conn, app.state.ledger, lot_id=lot_id, actor=actor, tag_id=tag_id.strip(), taken_at=taken_at,
                          chainage=fnum(chainage), gps_lat=fnum(gps_lat), gps_lon=fnum(gps_lon))
        return act(f"/lots/{lot_id}", go, "Sample recorded")

    @app.post("/lots/{lot_id}/tests")
    def test_add(request: Request, lot_id: int, parameter: str = Form(...), value: str = Form(...),
                 tested_on: str = Form(...), unit: str = Form(""), chainage: str = Form(""),
                 tag_id: str = Form(""), group_ref: str = Form(""), performed_by: str = Form("contractor_qc"),
                 lab: str = Form("")):
        actor, role = who(request)
        def go():
            require_role(role, "enter_data")
            sid = None
            if tag_id.strip():
                s = row(conn, "SELECT id FROM samples WHERE tag_id=?", (tag_id.strip(),))
                if not s:
                    raise ValueError(f"No sample with tag {tag_id}")
                sid = s["id"]
            qc.add_test(conn, app.state.ledger, lot_id=lot_id, actor=actor, parameter=parameter.strip(),
                        value=fnum(value), tested_on=tested_on, unit=unit, chainage=fnum(chainage), sample_id=sid,
                        group_ref=group_ref.strip() or None, performed_by=performed_by, lab=lab)
        return act(f"/lots/{lot_id}", go, "Result recorded")

    @app.post("/lots/{lot_id}/evaluate")
    def lot_eval(request: Request, lot_id: int):
        actor, _ = who(request)
        return act(f"/lots/{lot_id}", lambda: qc.evaluate_lot(conn, app.state.ledger, lot_id, actor),
                   lambda out: f"Lot result: {out['result'].upper()}" +
                               (f". {len(out['new_ncrs'])} NCR(s) raised." if out["new_ncrs"] else ""))

    @app.post("/lots/{lot_id}/release")
    def lot_release(request: Request, lot_id: int, note: str = Form("")):
        actor, role = who(request)
        return act(f"/lots/{lot_id}", lambda: qc.release_lot(conn, app.state.ledger, lot_id, actor, role, note),
                   "Hold point released. The lot can now be paid.")

    @app.get("/ncrs", response_class=HTMLResponse)
    def ncrs_page(request: Request):
        return page(request, "ncrs.html", ncrs=rows(conn, "SELECT * FROM ncrs WHERE contract_id=? ORDER BY status DESC, id DESC", (cid(),)))

    @app.post("/ncrs/{ncr_id}/close")
    def ncr_close(request: Request, ncr_id: int, disposition: str = Form(...), reason: str = Form(""),
                  next: str = Form("/ncrs")):
        actor, role = who(request)
        return act(next, lambda: qc.close_ncr(conn, app.state.ledger, ncr_id, actor, role, disposition, reason),
                   "NCR closed")

    # ---------- documents ----------

    @app.get("/documents", response_class=HTMLResponse)
    def documents_page(request: Request):
        docs = rows(conn, "SELECT * FROM documents WHERE contract_id=? ORDER BY id DESC", (cid(),))
        return page(request, "documents.html", docs=docs, kinds=intake.KINDS)

    @app.post("/documents")
    async def document_upload(request: Request, file: UploadFile = File(...), kind: str = Form(...),
                              publisher: str = Form(""), caption: str = Form("")):
        actor, role = who(request)
        data = await file.read()
        def go():
            require_role(role, "enter_data")
            return intake.store_document(conn, app.state.vault, app.state.ledger, contract_id=cid(), actor=actor,
                                         data=data, filename=file.filename or "upload", kind=kind,
                                         mime=file.content_type, publisher=publisher or None, caption=caption)
        try:
            with tx():
                did = go()
            return back(f"/documents/{did}", "Stored in the vault")
        except USER_ERRORS as e:
            return back("/documents", str(e), True)

    @app.get("/documents/{doc_id}", response_class=HTMLResponse)
    def document_page(request: Request, doc_id: int):
        doc = row(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
        if not doc:
            raise HTTPException(404)
        doc["extracted"] = json.loads(doc["extracted_json"]) if doc["extracted_json"] else None
        doc["match"] = json.loads(doc["match_json"]) if doc["match_json"] else None
        lots = rows(conn, "SELECT id, boq_code, layer, ch_from, ch_to, status FROM lots WHERE contract_id=? ORDER BY boq_code, ch_from", (doc["contract_id"],))
        deliveries = rows(conn, "SELECT * FROM deliveries WHERE contract_id=? ORDER BY id DESC", (doc["contract_id"],))
        return page(request, "document.html", doc=doc, lots=lots, deliveries=deliveries)

    @app.get("/documents/{doc_id}/file")
    def document_file(doc_id: int):
        doc = row(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
        if not doc:
            raise HTTPException(404)
        data = app.state.vault.get(doc["sha256"])
        return Response(data, media_type=doc["mime"] or "application/octet-stream",
                        headers={"Content-Disposition": f'inline; filename="{doc["filename"]}"'})

    @app.post("/documents/{doc_id}/extract")
    def document_extract(request: Request, doc_id: int):
        actor, role = who(request)
        doc = row(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
        path = f"/documents/{doc_id}"
        try:
            require_role(role, "enter_data")
            if doc["kind"] == "standard":
                licences.require(conn, doc["publisher"] or "", "ai_extract")
            data = app.state.vault.get(doc["sha256"])
            if doc["kind"] == "lab_report":
                known = [r["parameter"] for r in rows(conn, "SELECT DISTINCT parameter FROM rules WHERE contract_id=?", (doc["contract_id"],))]
                ext = extraction.extract_lab_report(settings, data, doc["filename"], doc["mime"], known).model_dump()
                match = match_lab_report(conn, doc["contract_id"], ext)
            elif doc["kind"] == "supplier_cert":
                ext = extraction.extract_certificate(settings, data, doc["filename"], doc["mime"]).model_dump()
                match = None
            else:
                raise ValueError("AI reading is set up for lab reports and supplier certificates. Use the rules page for specifications.")
        except USER_ERRORS as e:
            return back(path, str(e), True)
        with tx():
            update(conn, "documents", doc_id, {"status": "extracted", "extracted_json": json.dumps(ext),
                                               "match_json": json.dumps(match) if match else None})
            app.state.ledger.append(f"AI read for {actor}", "document.extracted", "document", doc_id,
                                    {"model": settings.model, "results": len(ext.get("results", ext.get("properties", []))),
                                     "match": match})
        note = ""
        if match:
            note = (f" Matched to lot {match['lot_id']} ({match['reason']})." if match["lot_id"] else f" No sure match: {match['reason']}.")
        return back(path, "Read by AI. Check every value against the document before confirming." + note)

    @app.post("/documents/{doc_id}/confirm")
    async def document_confirm(request: Request, doc_id: int):
        actor, role = who(request)
        form = await request.form()
        path = f"/documents/{doc_id}"
        def go():
            require_role(role, "enter_data")
            doc = row(conn, "SELECT * FROM documents WHERE id=?", (doc_id,))
            if doc["status"] == "confirmed":
                raise ValueError("Already confirmed")
            if doc["kind"] == "lab_report":
                lot_id = int(form.get("lot_id") or 0)
                if not lot_id:
                    raise ValueError("Choose the lot these results belong to")
                tested_on = str(form.get("tested_on") or date.today().isoformat())
                performed_by = str(form.get("performed_by") or "contractor_qc")
                n = 0
                i = 0
                while f"param_{i}" in form:
                    if form.get(f"keep_{i}"):
                        tag = str(form.get(f"tag_{i}") or "").strip()
                        s = row(conn, "SELECT id FROM samples WHERE tag_id=?", (tag,)) if tag else None
                        qc.add_test(conn, app.state.ledger, lot_id=lot_id, actor=actor,
                                    parameter=str(form[f"param_{i}"]).strip(), value=fnum(str(form[f"value_{i}"])),
                                    unit=str(form.get(f"unit_{i}") or ""), tested_on=tested_on,
                                    chainage=fnum(str(form.get(f"ch_{i}") or "")), sample_id=s["id"] if s else None,
                                    group_ref=str(form.get(f"group_{i}") or "").strip() or None,
                                    performed_by=performed_by, lab=str(form.get("lab") or ""), document_id=doc_id)
                        n += 1
                    i += 1
                update(conn, "documents", doc_id, {"status": "confirmed", "linked_lot_id": lot_id})
                app.state.ledger.append(actor, "document.confirmed", "document", doc_id, {"lot_id": lot_id, "tests": n})
                return f"Confirmed {n} result(s) into lot {lot_id}"
            if doc["kind"] == "supplier_cert":
                did = int(form.get("delivery_id") or 0)
                if did:
                    update(conn, "deliveries", did, {"cert_heat_no": str(form.get("heat_or_batch") or "") or None,
                                                     "gsa_marked": 1 if form.get("gsa") else 0, "document_id": doc_id})
                update(conn, "documents", doc_id, {"status": "confirmed"})
                app.state.ledger.append(actor, "document.confirmed", "document", doc_id, {"delivery_id": did or None})
                return "Certificate confirmed" + (f" and attached to delivery {did}" if did else "")
            update(conn, "documents", doc_id, {"status": "confirmed"})
            app.state.ledger.append(actor, "document.confirmed", "document", doc_id, {})
            return "Confirmed"
        return act(path, go, lambda m: m)

    # ---------- materials ----------

    @app.get("/materials", response_class=HTMLResponse)
    def materials_page(request: Request):
        k = cid()
        return page(request, "materials.html",
                    m1=[c.to_dict() for c in materials.check_orders(conn, k)],
                    m2=[c.to_dict() for c in materials.check_deliveries(conn, k)],
                    m3=materials.store_balances(conn, k), m4=materials.consumption_variance(conn, k),
                    pos=rows(conn, "SELECT * FROM purchase_orders WHERE contract_id=?", (k,)),
                    deliveries=rows(conn, "SELECT * FROM deliveries WHERE contract_id=? ORDER BY delivered_on", (k,)))

    @app.post("/materials/{kind}")
    async def materials_add(request: Request, kind: str):
        actor, role = who(request)
        form = {k: (str(v).strip() if v is not None else "") for k, v in (await request.form()).items()}
        tables = {
            "po": ("purchase_orders", ["po_ref", "supplier", "material", "grade", "standard", "quantity", "unit", "boq_code"]),
            "delivery": ("deliveries", ["waybill_no", "po_ref", "supplier", "material", "grade", "quantity", "unit",
                                        "heat_no", "cert_heat_no", "gsa_marked", "delivered_on"]),
            "store": ("store_moves", ["material", "direction", "quantity", "unit", "moved_on", "boq_code", "chainage", "ref"]),
            "source": ("approved_sources", ["material", "supplier", "grade", "approved_by", "approved_on"]),
            "rate": ("consumption_rates", ["boq_code", "material", "rate_per_unit", "material_unit", "allowance_pct", "source"]),
        }
        if kind not in tables:
            raise HTTPException(404)
        table, cols = tables[kind]
        def go():
            require_role(role, "enter_data")
            vals = {"contract_id": cid()}
            for c in cols:
                v = form.get(c, "")
                if c in ("quantity", "rate_per_unit", "allowance_pct", "chainage"):
                    v = fnum(v)
                elif c == "gsa_marked":
                    v = 1 if v else 0
                vals[c] = v if v != "" else None
            rid = insert(conn, table, vals)
            app.state.ledger.append(actor, f"materials.{kind}_added", table, rid, vals)
        return act("/materials", go, "Recorded")

    # ---------- IPCs ----------

    @app.get("/ipcs", response_class=HTMLResponse)
    def ipcs_page(request: Request):
        k = cid()
        ipcs = rows(conn, """SELECT i.*, (SELECT COUNT(*) FROM ipc_lines l WHERE l.ipc_id=i.id) AS n_lines
                             FROM ipcs i WHERE contract_id=? ORDER BY number DESC""", (k,))
        nxt = (row(conn, "SELECT MAX(number) m FROM ipcs WHERE contract_id=?", (k,))["m"] or 0) + 1
        return page(request, "ipcs.html", ipcs=ipcs, next_number=nxt)

    @app.post("/ipcs")
    def ipc_add(request: Request, number: int = Form(...), period_end: str = Form(...)):
        actor, role = who(request)
        try:
            with tx():
                require_role(role, "enter_data")
                iid = ipc.create_ipc(conn, app.state.ledger, cid(), number, period_end, actor)
            return back(f"/ipcs/{iid}", f"IPC {number} created. Add the contractor's claim lines.")
        except USER_ERRORS as e:
            return back("/ipcs", str(e), True)

    @app.get("/ipcs/{ipc_id}", response_class=HTMLResponse)
    def ipc_page(request: Request, ipc_id: int):
        pack = ipc.evidence_pack(conn, ipc_id)
        boq = rows(conn, "SELECT * FROM boq_items WHERE contract_id=? ORDER BY code", (pack["ipc"]["contract_id"],))
        return page(request, "ipc.html", pack=pack, boq=boq)

    @app.post("/ipcs/{ipc_id}/lines")
    async def ipc_lines_add(request: Request, ipc_id: int, boq_code: str = Form(""), quantity: str = Form(""),
                            ch_from: str = Form(""), ch_to: str = Form(""), description: str = Form(""),
                            file: UploadFile | None = File(None)):
        actor, role = who(request)
        data = await file.read() if file and file.filename else b""
        def go():
            require_role(role, "enter_data")
            n = 0
            if data:
                for r in csv.DictReader(io.StringIO(data.decode("utf-8-sig"))):
                    r = {(kk or "").strip().lower(): (v or "").strip() for kk, v in r.items()}
                    ipc.add_line(conn, app.state.ledger, ipc_id, actor, r["boq_code"], fnum(r["quantity"]),
                                 fnum(r.get("ch_from")), fnum(r.get("ch_to")), r.get("description", ""))
                    n += 1
            elif boq_code:
                ipc.add_line(conn, app.state.ledger, ipc_id, actor, boq_code, fnum(quantity), fnum(ch_from),
                             fnum(ch_to), description)
                n = 1
            if not n:
                raise ValueError("Give a line or upload a CSV")
            return n
        return act(f"/ipcs/{ipc_id}", go, lambda n: f"Added {n} line(s)")

    @app.post("/ipcs/{ipc_id}/check")
    def ipc_check(request: Request, ipc_id: int):
        actor, _ = who(request)
        return act(f"/ipcs/{ipc_id}", lambda: ipc.check_ipc(conn, app.state.ledger, ipc_id, actor),
                   lambda s: f"Checked: {s['complete']} complete, {s['exception']} with exceptions")

    @app.post("/ipc-lines/{line_id}/review")
    def ipc_review(request: Request, line_id: int, decision: str = Form(...), note: str = Form(""),
                   ipc_id: int = Form(...)):
        actor, role = who(request)
        return act(f"/ipcs/{ipc_id}", lambda: ipc.review_line(conn, app.state.ledger, line_id, actor, role, decision, note),
                   "Line reviewed")

    @app.post("/ipcs/{ipc_id}/certify")
    def ipc_certify(request: Request, ipc_id: int):
        actor, role = who(request)
        return act(f"/ipcs/{ipc_id}", lambda: ipc.certify_ipc(conn, app.state.ledger, ipc_id, actor, role),
                   lambda o: f"Certified {o['certified']} line(s); {o['held']} held to the next IPC")

    @app.get("/ipcs/{ipc_id}/pack", response_class=HTMLResponse)
    def ipc_pack(request: Request, ipc_id: int):
        return page(request, "pack.html", pack=ipc.evidence_pack(conn, ipc_id))

    @app.get("/ipcs/{ipc_id}/pack.csv")
    def ipc_pack_csv(ipc_id: int):
        pack = ipc.evidence_pack(conn, ipc_id)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["boq_code", "description", "ch_from_m", "ch_to_m", "quantity", "unit", "rate", "amount",
                    "status", "findings", "reviewer", "review_note"])
        for l in pack["lines"]:
            w.writerow([l["boq_code"], l["boq_description"], l["ch_from"], l["ch_to"], l["quantity"], l["unit"],
                        l["rate"], l["amount"], l["status"],
                        " | ".join(f"{f['check']}: {f['message']}" for f in l["findings"]), l["reviewer"] or "",
                        l["review_note"] or ""])
        return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="ipc-{pack["ipc"]["number"]}-evidence.csv"'})

    # ---------- reports and ledger ----------

    @app.get("/reports/monthly", response_class=HTMLResponse)
    def monthly(request: Request, month: str = ""):
        month = month or date.today().isoformat()[:7]
        return page(request, "monthly.html", rep=reports.monthly_quality_report(conn, cid(), month))

    @app.get("/ledger", response_class=HTMLResponse)
    def ledger_page(request: Request):
        return page(request, "ledger.html", chain=app.state.ledger.verify_chain(),
                    entries=rows(conn, "SELECT * FROM ledger ORDER BY id DESC LIMIT 300"))

    # ---------- WhatsApp intake ----------

    @app.get("/intake/whatsapp")
    def whatsapp_verify(request: Request):
        q = request.query_params
        if q.get("hub.mode") == "subscribe" and settings.whatsapp_verify_token and \
                q.get("hub.verify_token") == settings.whatsapp_verify_token:
            return PlainTextResponse(q.get("hub.challenge", ""))
        raise HTTPException(403)

    @app.post("/intake/whatsapp")
    async def whatsapp_receive(request: Request):
        body = await request.body()
        if not intake.verify_signature(settings, body, request.headers.get("X-Hub-Signature-256")):
            raise HTTPException(403, "bad signature")
        stored = []
        for m in intake.parse_media_messages(json.loads(body or b"{}")):
            data, mime = intake.download_media(settings, m["media_id"])
            with tx():
                stored.append(intake.store_document(
                    conn, app.state.vault, app.state.ledger, contract_id=cid(), actor=f"WhatsApp {m['from']}",
                    data=data, filename=m["filename"], kind=intake.kind_from_caption(m["caption"]),
                    source="whatsapp", mime=mime or m["mime"], caption=m["caption"]))
        return {"stored": stored}

    return app

