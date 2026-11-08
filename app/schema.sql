-- Verify Before Certify: SQLite schema for the pilot.

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    employer TEXT,
    consultant TEXT,
    contractor TEXT,
    currency TEXT DEFAULT 'GHS'
);

CREATE TABLE IF NOT EXISTS boq_items (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    unit TEXT NOT NULL,
    quantity REAL NOT NULL,
    rate REAL,
    material TEXT,
    UNIQUE (contract_id, code)
);

-- Licence register: one row per publisher licence.
CREATE TABLE IF NOT EXISTS licences (
    id INTEGER PRIMARY KEY,
    publisher TEXT NOT NULL,
    holder TEXT NOT NULL,
    uses_json TEXT NOT NULL,          -- e.g. ["store", "ai_extract", "store_excerpt"]
    customers TEXT,
    expires_on TEXT,                  -- ISO date or NULL for no expiry
    reference TEXT,
    created_at TEXT NOT NULL
);

-- Rule cards. A change creates a new version; old versions stay for replay.
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    rule_code TEXT NOT NULL,
    version INTEGER NOT NULL,
    boq_code TEXT NOT NULL,
    parameter TEXT NOT NULL,
    unit TEXT,
    method TEXT,
    limit_type TEXT NOT NULL,
    params_json TEXT NOT NULL,
    frequency_qty REAL,               -- one test per this many lot units (e.g. 350 m2)
    marginal_band REAL DEFAULT 0,
    source_publisher TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    source_quote TEXT,
    effective_from TEXT NOT NULL,
    status TEXT NOT NULL,             -- draft | approved | superseded | rejected
    drafted_by TEXT NOT NULL,         -- ai | manual
    approved_by TEXT,
    approved_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (contract_id, rule_code, version)
);

CREATE TABLE IF NOT EXISTS lots (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    boq_code TEXT NOT NULL,
    layer TEXT,
    ch_from REAL NOT NULL,            -- metres
    ch_to REAL NOT NULL,
    width_m REAL,
    quantity REAL NOT NULL,           -- in the BOQ item's unit
    lot_size REAL NOT NULL,           -- size used for test frequency (m2, m3 or t)
    placed_on TEXT NOT NULL,
    status TEXT NOT NULL,             -- open | passed | marginal | failed | approved
    released_by TEXT,
    released_at TEXT
);

CREATE TABLE IF NOT EXISTS samples (
    id INTEGER PRIMARY KEY,
    lot_id INTEGER NOT NULL REFERENCES lots(id),
    tag_id TEXT NOT NULL UNIQUE,
    taken_at TEXT NOT NULL,
    chainage REAL,
    gps_lat REAL,
    gps_lon REAL,
    taken_by TEXT,
    photo_sha256 TEXT
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY,
    lot_id INTEGER NOT NULL REFERENCES lots(id),
    sample_id INTEGER REFERENCES samples(id),
    parameter TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    group_ref TEXT,                   -- e.g. cube set id for concrete
    tested_on TEXT NOT NULL,
    chainage REAL,
    lab TEXT,
    performed_by TEXT NOT NULL,       -- contractor_qc | consultant | independent
    document_id INTEGER REFERENCES documents(id),
    entered_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY,
    lot_id INTEGER NOT NULL REFERENCES lots(id),
    result TEXT NOT NULL,             -- pass | marginal | fail
    findings_json TEXT NOT NULL,
    evaluated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ncrs (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    lot_id INTEGER REFERENCES lots(id),
    rule_code TEXT,
    finding_kind TEXT,
    description TEXT NOT NULL,
    deviation REAL,
    chainage REAL,
    status TEXT NOT NULL,             -- open | closed
    disposition TEXT,                 -- rework | retest | accept_with_reason
    reason TEXT,
    raised_at TEXT NOT NULL,
    closed_by TEXT,
    closed_at TEXT
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    kind TEXT NOT NULL,               -- lab_report | supplier_cert | waybill | spec | standard | claim | other
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    mime TEXT,
    source TEXT NOT NULL,             -- upload | whatsapp | email
    publisher TEXT,
    caption TEXT,
    received_at TEXT NOT NULL,
    status TEXT NOT NULL,             -- received | extracted | confirmed | rejected | manual_entry
    extracted_json TEXT,
    match_json TEXT,
    linked_lot_id INTEGER REFERENCES lots(id)
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    po_ref TEXT NOT NULL,
    supplier TEXT NOT NULL,
    material TEXT NOT NULL,
    grade TEXT,
    standard TEXT,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    boq_code TEXT
);

CREATE TABLE IF NOT EXISTS approved_sources (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    material TEXT NOT NULL,
    supplier TEXT NOT NULL,
    grade TEXT,
    approved_by TEXT,
    approved_on TEXT
);

CREATE TABLE IF NOT EXISTS deliveries (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    waybill_no TEXT NOT NULL,
    po_ref TEXT,
    supplier TEXT NOT NULL,
    material TEXT NOT NULL,
    grade TEXT,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    heat_no TEXT,
    cert_heat_no TEXT,
    gsa_marked INTEGER,
    delivered_on TEXT NOT NULL,
    document_id INTEGER REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS store_moves (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    material TEXT NOT NULL,
    direction TEXT NOT NULL,          -- in | out | count
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    moved_on TEXT NOT NULL,
    boq_code TEXT,
    chainage REAL,
    ref TEXT
);

CREATE TABLE IF NOT EXISTS consumption_rates (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    boq_code TEXT NOT NULL,
    material TEXT NOT NULL,
    rate_per_unit REAL NOT NULL,      -- material units per BOQ unit
    material_unit TEXT NOT NULL,
    allowance_pct REAL NOT NULL,      -- allowed variance before a flag
    source TEXT
);

CREATE TABLE IF NOT EXISTS ipcs (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL REFERENCES contracts(id),
    number INTEGER NOT NULL,
    period_end TEXT NOT NULL,
    status TEXT NOT NULL,             -- draft | checked | certified
    certified_by TEXT,
    certified_at TEXT,
    UNIQUE (contract_id, number)
);

CREATE TABLE IF NOT EXISTS ipc_lines (
    id INTEGER PRIMARY KEY,
    ipc_id INTEGER NOT NULL REFERENCES ipcs(id),
    boq_code TEXT NOT NULL,
    description TEXT,
    ch_from REAL,
    ch_to REAL,
    quantity REAL NOT NULL,
    status TEXT NOT NULL,             -- claimed | complete | exception | reviewed | certified | held
    findings_json TEXT,
    reviewer TEXT,
    review_note TEXT,
    reviewed_at TEXT
);

-- Append-only, hash-chained audit ledger.
CREATE TABLE IF NOT EXISTS ledger (
    id INTEGER PRIMARY KEY,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity TEXT NOT NULL,
    entity_id TEXT,
    payload_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;
