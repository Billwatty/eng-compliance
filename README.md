# Verify Before Certify

Pilot software for supervising consultants on Ghana road contracts. It runs quality control on every layer, pour and delivery against the contract specification. It then checks every line of the contractor's Interim Payment Certificate (IPC) against that approved evidence before the Resident Engineer signs.

The design is in [docs/architecture.html](docs/architecture.html). The market research behind it is in [research/](research/).

## Run it

```bash
/opt/homebrew/bin/python3.12 -m venv .venv      # Python 3.10 or newer
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.seed_demo --reset   # load the demo contract
.venv/bin/uvicorn app.main:create_app --factory --reload
```

Open http://localhost:8000. Switch role in the top bar. Only the Resident Engineer can certify, and only a materials engineer or the Resident Engineer can approve rules and release lots.

Run the tests:

```bash
.venv/bin/python -m pytest -q
```

## Demo walkthrough

The demo uses the worked examples from the design document. All figures are illustrative.

1. **Lots, lot 2.** Base course 12+000 to 12+500 with 8 of 10 required density tests. The engine reports three failures: one test 0.2 points below 97%, a lot mean 0.05 below 98%, and 2 tests missing. Three NCRs are open.
2. **IPCs, IPC 2.** Four claim lines, already checked:
   - base 12+000 to 12+500 is blocked by the failed lot and its NCRs
   - base 12+500 to 13+000 is complete
   - subbase 12+800 to 13+000 was already certified in IPC 1
   - the culvert used 760 bags of cement where the mix design needs 840, which is 9.5% short and a possible under-dosing
3. **Materials.**
   - one purchase order is for a supplier that is not approved
   - one rebar delivery's bar-tag heat number does not match its certificate and has no GSA marking
   - the cement store count is 2 bags short of the book balance
4. **Review and certify.** As quantity surveyor, accept or hold each line. Accepting a line with exceptions needs a written reason. Then switch to Resident Engineer and certify. Held lines carry to the next IPC.
5. **Ledger.** Every action is hash-chained. The page shows whether the chain is intact.

## How it maps to the design

| Design component | Code |
|---|---|
| Rule library, versions by effective date | [app/qc.py](app/qc.py) `add_rule`, `approve_rule`, `rules_in_force` |
| Rules engine: min, max, range, lot mean, tolerance, envelope, concrete cubes, frequency, near-limit runs | [app/rules.py](app/rules.py) |
| Lots, hold points, NCRs and dispositions | [app/qc.py](app/qc.py) |
| Materials chain checks M1 to M4 | [app/materials.py](app/materials.py) |
| IPC checks (M5), line states, certification, evidence pack | [app/ipc.py](app/ipc.py) |
| AI reading of lab reports and certificates; AI rule drafting | [app/extraction.py](app/extraction.py) |
| Matcher: sample tag, then chainage | [app/matcher.py](app/matcher.py) |
| Licence register and gate | [app/licences.py](app/licences.py) |
| Write-once file vault and hash-chained ledger | [app/ledger.py](app/ledger.py) |
| Upload and WhatsApp intake | [app/intake.py](app/intake.py) |
| Monthly quality report | [app/reports.py](app/reports.py) |
| Roles and permissions | [app/roles.py](app/roles.py) |

## AI reading

AI reads documents and drafts rules. It never decides a result.
- **Extractions:** each one is a draft that a person checks against the original and confirms.
- **Rule drafts:** each one waits for an engineer's approval.
- **Model:** `claude-opus-5-5`, called through structured outputs, with the server-side refusal fallback on.
- **Without credentials:** the app works normally and values are entered by hand.

Set `ANTHROPIC_API_KEY` or run `ant auth login` to turn AI reading on.

## Standards licences

ISO, ASTM, BSI, GSA and AASHTO standards pass a licence gate. Until a publisher's licence is recorded on the Standards page:
- the standard cannot be uploaded
- AI cannot draft rules from it
- no excerpt of its text is stored

Engineers enter numeric limits and clause numbers by hand. Contract documents and government specifications are treated as usable with the client's permission. Write that permission into the pilot agreement.

## Not production-ready yet

- **Sign-in:** the role picker is a cookie with no authentication. Add real accounts before anyone outside the pilot team uses it.
- **Untested live:**
  - **Claude extraction:** tested only with a fake client. No API credentials were available when it was built.
  - **WhatsApp intake:** follows the Cloud API webhook format, but has not been run against a live number.
- **Not built yet:**
  - the offline Android field app and sample chain of custody, which are planned after the pilot
  - email intake
  - Excel import of IPC claims, which takes CSV for now
- **Specification limits in the demo:** these come from unofficial copies of the 2006–07 Ghana Standard Specification. Confirm them against the edition named in each contract.
- **Storage:** SQLite on one machine. Move to Postgres with PostGIS and decide data residency with the client before a multi-user deployment.
