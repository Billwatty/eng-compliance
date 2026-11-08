# Engineering Compliance Verification: Market Research and Entry Decision

Prepared 8 November 2026. Written from a skeptical researcher's point of view.

**Legend.** Each material claim carries a label.
- **[F]** Fact from a cited source. Vendor pages count as facts about what the vendor *claims*, not about what the product does.
- **[V]** Vendor claim, not independently verified.
- **[E]** My estimate, with the assumptions shown.
- **[H]** Hypothesis to test in interviews or a pilot.
- **[U]** Could not verify. The text says what evidence would settle it.

**Method limits.** This is desk research from public web sources. Several primary sources blocked automated fetching, including oversight.gov, Montana DOT manuals and Ghanaian news sites. In those cases I relied on search-index summaries and say so. I did not see any product demo. Every capability statement about a competitor is either documented by a public user (such as a state DOT manual) or labelled as a vendor claim.

---

## 0. Bottom line

1. **The broad idea of reading requirements and checking evidence against them is real but crowded at the document-reading layer.** At least nine vendors now sell AI checks of mill test reports and certificates of conformance (CoCs) against ASTM, ASME, API and EN standards and purchase orders. Procore shipped an AI submittal-review agent in May 2026. Extraction and matching are becoming a feature, not a company.
2. **The most defensible gap is narrower.** It is the reconciliation between *what was accepted*, *what was delivered and installed*, and *what is being paid for*, tied to a contract item, quantity and location, and measured against an owner's acceptance rules. The strongest public evidence of pain is in US federal-aid highway work at **final materials certification before closeout and final payment**.
3. **Recommended start (medium-low confidence):** a *materials certification readiness* check for US federal-aid highway contracts. It would be sold first to heavy-civil contractors' quality control (QC) and project-controls teams, or to construction engineering and inspection (CEI) consultants. Run it as a shadow review next to the agency's own materials review. Do not sell to state DOTs first, because they buy slowly and already run AASHTOWare Project.
4. **Ghana is a weak *first paying* market but a useful *learning* market.** The documented Ghanaian pain is payment-certificate validation, arrears and late-payment interest, not technical material conformance. Public owners are cash-constrained and software adoption is low.
5. **Hold-off condition:** if interviews show that closeout materials delays come mainly from staff backlog, sequencing or missing tests rather than detectable document errors, do not build. Wisconsin DOT cut its materials certification lead time by 49% with process changes alone ([WisDOT, 2015](https://wisconsindot.gov/Documents/about-wisdot/performance/lean-gvmt/dtsd-materialcert-final6.pdf)).

---

## 1. Sector screen and real workflows

### 1.1 One recurring compliance decision per sector

| Sector | Decision, decider, timing | Requirement type | Evidence used | Cost if wrong or late |
|---|---|---|---|---|
| **Roads and bridges, US federal-aid** | *Is this material accepted for the contract item and quantity paid?* An agency inspector or materials coordinator decides, and the DOT materials engineer signs the final materials certificate. Checks run at delivery, at each estimate, and at closeout. | **Regulatory:** each state must run an FHWA-approved QA programme for National Highway System projects and deliver a materials certificate at completion ([23 CFR 637 Subpart B](https://www.ecfr.gov/current/title-23/chapter-I/subchapter-G/part-637/subpart-B)) [F]. Buy America is in 23 CFR 635.410 ([FDOT manual](https://www.fdot.gov/docs/default-source/content-docs/construction/manuals/cpam/newhistory/Chapter5s8Redline.pdf)) [F]. **Contractual:** state standard specifications, special provisions, sampling-frequency guides and qualified products lists (QPL). **Industry standards:** AASHTO and ASTM test methods referenced by the specification. | Delivery tickets or e-tickets, manufacturer certifications, Buy America certifications, sample and test records, and approved mix designs. | Closeout and final payment slip. In Wisconsin, more than 50% of contracts completed in 2011–12 waited over six months for materials certification ([WisDOT](https://wisconsindot.gov/Documents/about-wisdot/performance/lean-gvmt/dtsd-materialcert-final6.pdf)) [F]. An FHWA review found nonconforming materials installed and missing certifications on local-agency projects ([FHWA](https://webarchive.library.unt.edu/web/20161102092624/http:/www.fhwa.dot.gov/federalaid/lpa/120213.pdf)) [F, dated]. |
| **Buildings, UK higher-risk buildings (HRB)** | *Can the Building Safety Regulator (BSR) issue a completion certificate?* The principal contractor and principal designer compile the evidence and the BSR decides at Gateway 3, before occupation. | **Regulatory:** Building Safety Act 2022 gateway regime, golden thread and change control. **Contractual:** employer's requirements and specification. | As-built information, product data, change-control records, fire and structural evidence. | Occupation is delayed. Common faults include mismatches between drawings and what was installed and poorly recorded post-Gateway-2 changes ([thebuildingsafetyact.com](https://www.thebuildingsafetyact.com/gateway-3/); [Charles Russell Speechlys, 2025](https://www.charlesrussellspeechlys.com/en/insights/expert-insights/construction-engineering-and-projects/2025/higher-risk-buildings--passing-through-gateway-3/)) [F]. The FOI-based average was 27.5 weeks in 2024–25 against an 8-week target ([Construction News, May 2026](https://www.constructionnews.co.uk/buildings/building-safety/bsr-missing-gateway-three-target-data-reveals-14-05-2026/)) [F]. |
| **Aerospace manufacturing and MRO** | *Can this part or raw material be accepted into stock or installed?* The receiving inspector and quality engineer decide at receipt and again at installation. | **Regulatory:** FAA and EASA airworthiness release (Form 8130-3 or EASA Form 1). **Industry:** AS9100 purchasing and AS9102 first article inspection. **Contractual:** customer quality clauses, for example Boeing X31764 Rev 5, January 2026, which requires suppliers to provide verification data on request ([Boeing](https://www.boeingsuppliers.com/content/dam/boeing/boeingsuppliers/boeing-suppliers/becoming/quality/X31764_Revision_5_Jan_2026.pdf)) [F]. | CoC, release certificate, material certifications, purchase order (PO) revision, approved processor lists. | Unapproved parts fly. AOG Technics forged at least 70 release certificates for about 50 CFM56 parts ([EASA](https://www.easa.europa.eu/en/domains/aircraft-products/suspected-unapproved-parts/aircraft-parts-distributed-aog-technics)) [F, 2023]. Titanium with falsified certificates reached Boeing and Airbus jets through Spirit AeroSystems' supply chain ([ABC/AP, 14 Jun 2024](https://abcnews.go.com/Business/wireStory/faa-investigating-titanium-parts-falsified-records-wound-boeing-111129643)) [F]. |
| **Energy and industrial facilities (EPC, refining)** | *Is this alloy pipe, flange or spool the specified material, and is it traceable to its heat?* The QC inspector at receipt and fabrication decides, and the owner's inspector decides at turnover. | **Industry:** API RP 578 material verification programme. **Contractual:** project piping specification and ASME B31.3. **Regulatory:** process safety rules, cited by the CSB in recommending positive material identification (PMI) ([CED summary of CSB bulletin 2005-04-B](https://www.cedengineering.com/userfiles/Positive%20Material%20Identification.pdf)) [F]. | MTR or MTC (EN 10204 3.1 or 3.2), heat numbers marked on the material, PMI readings, isometrics with heat transfer records. | Wrong-alloy failures and fires. One source estimates inadvertent substitution in about 1–3% of installed alloy components ([same source](https://www.cedengineering.com/userfiles/Positive%20Material%20Identification.pdf)) [F, secondary, unverified original]. Vendor data can sit on the start-up critical path ([EPC/supplier survey](https://www.slideshare.net/CarlMueller7/supplier-vs-epc-survey)) [F, dated]. |
| **Nuclear (energy subset)** | *Is this commercial-grade item dedicated for safety-related use?* Licensee and vendor quality assurance decide. | **Regulatory:** 10 CFR 21 and 10 CFR 50 Appendix B, with a final regulatory guide in April 2024 ([Federal Register](https://www.govinfo.gov/content/pkg/FR-2024-04-29/html/2024-08963.htm)) [F]. | Dedication packages, test records, counterfeit, fraudulent and suspect item (CFSI) screening. | NRC findings for weak dedication documentation ([NRC search results](https://www.nrc.gov/about-nrc/cfsi/guidance.html)) [F]. |
| **Manufacturing and automotive** | *Release this incoming lot?* Incoming quality control decides at receipt. | **Industry:** IATF 16949 and PPAP. **Contractual:** customer-specific requirements. | CoC and certificate of analysis, PPAP records, gauge data. | Line stoppage and recall cost. I found no fresh public quantification in this screen [U]. |
| **Rail (UK)** | *Is this product accepted for use on Network Rail infrastructure?* The Network Technical Head approves at product introduction, not per delivery. | **Owner standard:** NR/L2/RSE/100/05, product acceptance certificate and PADS catalogue ([Network Rail](https://www.networkrail.co.uk/product-acceptance/)) [F]. | Acceptance application, criticality matrix. | Product cannot be used. This is a one-off approval, so it is low-frequency. |
| **Medical devices (US)** | *Accept this incoming component lot?* Incoming inspection and the supplier quality engineer decide. | **Regulatory:** the QMSR has been in force since 2 Feb 2026 and incorporates ISO 13485 clause 7.4 ([King & Spalding](https://www.kslaw.com/insights/articles/the-qmsr-goes-live-and-fda-implements-a-new-medical-device-inspection-technique)) [F]. | CoC and certificate of analysis, sampling inspection, approved supplier list. | Form 483s. Outsourcing and purchasing is among the top early QMSR observation areas ([RAPS](https://www.raps.org/resource/fda-official-details-top-observations-from-qmsr-inspections.html)) [F, one official's remarks]. |

### 1.2 Construction material walk-through: reinforcing steel and HMA on a highway contract

Two contract models are shown side by side. One is a **US state DOT unit-price federal-aid contract**. The other is a **Ghana Highway Authority (GHA) contract on FIDIC-style conditions with a bill of quantities (BOQ)**. GHA's use of FIDIC is implied by GHA staff attending FIDIC 1999 Red Book training ([FIDIC brochure](https://fidic.org/sites/default/files/event-files/Brochure_43.pdf)) [F]. Whether each contract adopts FIDIC needs checking against its Particular Conditions [U].

| Stage | Technical compliance control | Payment control | Overlap or gap |
|---|---|---|---|
| **1. Bid / BOQ** | Pay items reference specification sections, for example "Reinforcing steel, Grade 60, Section 505". | Unit rate × estimated quantity. | Both hang off the **contract item**, which is the natural join key. |
| **2. Technical approval** | US: source approval via QPL or approved producer, mix design approval in AASHTOWare ([AASHTOWare C&M](https://aashtowareproject.org/apr-cm)) [F]. Ghana: Engineer approves source and samples. | None. | Approval sets *which* product is allowed and is later needed to judge a substitution. |
| **3. Contractor purchase order** | PO should carry the grade, specification, Buy America and certification flow-down. | Contractor's own commercial terms. | **The owner never sees this PO**, so flow-down errors surface late. |
| **4. Delivery and receiving** | Inspector accepts or rejects loads. On e-ticketing projects in Arkansas this happens in the E-DOT app ([ARDOT notice](https://media.ark.org/ardot/Notice-to-Contractors-HaulHub.pdf)) [F]. Buy America certification is due on delivery ([Caltrans](https://dot.ca.gov/-/media/dot-media/programs/local-assistance/documents/coin/coin11-04.pdf)) [F]. | Supplier invoice starts the contractor's three-way match of PO, receipt and invoice. | **This is the first divergence.** The contractor pays the supplier on commercial receipt, but the owner pays the contractor only on accepted material. |
| **5. Verified installation** | Samples and tests against the sampling-frequency guide. In AASHTOWare, an "acceptance action" is satisfied when approved represented quantity is at least the reported installed quantity ([DDOT AASHTOWare help](https://daashto.ddot.dc.gov/Help_Sys_Admin/understanding-business-rules-for-material-acceptance-actions.htm)) [F]. | Quantity measured into the daily record and estimate. | AASHTOWare checks that **records exist and quantities cover**. Public docs do not show it checks the *content* of an attached certificate [U]. |
| **6. Supplier invoice** | None. | Contractor AP pays on PO terms. | Supplier is paid even if the owner later rejects the material. The contractor carries that risk. |
| **7. Contractor progress claim** | US: estimates pay installed accepted quantities. Stored materials need owner approval, title evidence and backup such as invoices ([sample subcontract](https://www.bernards.com/wp-content/uploads/2018/04/S15.01_B13.0_AttB_Prevailing_Wage_Skilled_Workforce_LLB.pdf)) [F]. Ghana: Engineer certifies the Interim Payment Certificate (IPC), and FIDIC 1999 Sub-Clause 14.5 allows payment for listed plant and materials on site [F for clause location ([SAICE](https://bookstore.saice.org.za/product/fidic-quick-reference-guide-red-book/)); clause conditions U]. | Owner pays measured work minus retention. | **The two payment flows run on different rules.** The supplier invoice is a commercial three-way match. The progress claim is an engineering certification of quantity, quality and evidence. |
| **8. Final closeout** | US: final materials review, then the materials certificate (23 CFR 637 App. A). WisDOT signs it after the final estimate work ([WisDOT finals](https://wisconsindot.gov/rdwy/admin/finals.pdf)) [F]. NCDOT: spec brochures do not count as certification ([NCDOT closeout guide](https://connect.ncdot.gov/municipalities/Funding/PublishingImages/Closeout%20Guide.pdf)) [F]. Ghana: completion certificate, snag list, and a final account with incomplete files ([Ghana Auditor-General, 28 Nov 2019](https://audit.gov.gh/files/audit_reports/Performance_Audit_Report_of_the_Auditor-General_on_Selected_Road_Works_in_Ghana-1.pdf)) [F]. | Final payment, retention release, and closing federal participation. | **This is the strongest pain checkpoint.** Every acceptance gap accumulated during the job lands here at once. |

**Checkpoint with the strongest pain and an actionable buyer.** Final materials certification is the checkpoint.
- In Wisconsin, 39% of regional projects took more than six months from "All Contract Work Complete" to "Material Certification", and another 34% took three to six months ([WisDOT](https://wisconsindot.gov/Documents/about-wisdot/performance/lean-gvmt/dtsd-materialcert-final6.pdf)) [F, 2011–12 data, published 2015].
- Average let-project closeout ran 307 days before the fix and 141 days after it [F].
- The remedy was *interim materials review during construction*. That is the job software would automate [F].
- Kentucky research also found long durations at the "materials check" step ([KTC](https://rosap.ntl.bts.gov/view/dot/32838/dot_32838_DS1.pdf)) [F].
- A 2022 TRB-published paper lists documentation difficulties as a main cause of highway closeout delays ([UKY](https://scholars.uky.edu/en/publications/causes-implications-and-strategies-for-project-closeout-delays-in/)) [F].

**In Ghana the pain sits at IPC validation, not material conformance.**
- Late IPC payment produced GH¢38.19m of interest on GH¢612.74m of original contract sums. The Auditor-General asked GHA to adopt a 56-day IPC processing policy ([2019 performance audit](https://audit.gov.gh/files/audit_reports/Performance_Audit_Report_of_the_Auditor-General_on_Selected_Road_Works_in_Ghana-1.pdf)) [F].
- In the same audit the auditors cored the roads themselves and found 20% of aggregate gradings outside specification limits on the East Legon–Spintex tunnel asphalt. GHA was still judged to have "ensured adherence to specification" overall [F].
- Project files "were incomplete as different categories of documents were mixed in the project files" [F].
- In 2025 the Auditor-General disallowed about GH¢3.5bn of inherited arrears ([Citi Newsroom, Jul 2025](https://citinewsroom.com/2025/07/auditor-general-rejects-gh%C2%A23-5bn-in-arrears-over-irregular-contracts-ato-forson/)) [F]. Later reports cite GH¢8.1bn–12.16bn rejected for unsupported documentation and duplication. These figures conflict across sources [F, scope unclear].

---

## 2. How the market already solves it

### 2.1 Workflow-level capability test

The test asks whether a tool can read a project-specific specification, reconcile it with a scanned delivery note and a material certificate, link the result to the right batch or work area, and flag the discrepancy before sign-off.

| Product | Reads project spec | Reads cert / ticket content | Links to batch, contract item, location | Blocks or flags before sign-off | Status of evidence |
|---|---|---|---|---|---|
| **AASHTOWare Project C&M** (most US DOTs) | No. Requirements are configured as acceptance actions and sampling frequencies per material. | Certs are attached to sample records. Indiana requires Buy America certs attached to Sample IDs ([INDOT](https://secure.in.gov/indot/doing-business-with-indot/files/dir109c.pdf)) [F]. No public evidence that it reads attachment content [U]. | Yes, by contract item, material and sample. Quantity-coverage rule [F]. | Yes, it flags unsatisfied acceptance actions by quantity [F]. | **Verified** from DOT documentation. About 50 licensees in 2020 ([MTU deck](https://www.ctt.mtu.edu/sites/ctt/files/resources/cmc/2020/10_burns_spitzley.pdf)) [F, dated]. |
| **MetaField** (Agile Frameworks) | No. It runs forms for testing labs. | Captures field and lab data on ASTM/AASHTO/DOT forms [V]. | Project and sample level [V]. | Report output only [V]. | Vendor claims and reviews. More than 160 firms ([Nomic glossary](https://www.nomic.ai/glossary/metafield)) [V]. It serves the *testing lab*, not the owner's acceptance decision. |
| **HaulHub / E-DOT** | No. | Structured e-tickets, with no OCR needed [F]. | Load to project and mix [F]. | Inspector accepts or rejects loads in the app [F]. | **Verified** in ARDOT, TDOT, Caltrans and WVDOH documents. Strongest incumbent at the delivery checkpoint. |
| **Procore + Datagrid** submittal agent | Yes, it compares submittals to specs ([ENR, 2026](https://www.enr.com/articles/63042-procore-releases-new-ai-agents-after-datagrid-integration)) [F]. | Submittals, not delivery tickets [F]. | Submittal record [F]. | First-pass reviewer [V]. | Shipped 21 May 2026 [F]. Covers the *approval* step, not delivery or installation. |
| **Trunk Tools, Helonic, iFieldSmart, Part3, BuildSync** | Yes for submittals [V]. | Product data and shop drawings [V]. | Spec section [V]. | Pre-approval [V]. | Vendor claims ([Trunk Tools blog](https://trunktools.com/blog/best-construction-submittal-software/)). This is a crowded step. |
| **MTR.AI, TestCert, Pathnovo, aekam, Certivo** | Standards libraries; Pathnovo and aekam add customer and internal specs [V]. | Yes, MTR/MTC extraction with pass/fail [V]. | Pathnovo matches PO and heat [V]. | Pre-acceptance [V]. | Vendor claims ([MTR.AI](https://www.mtr.ai/), [TestCert](https://www.testcert.co/), [Pathnovo](https://pathnovo.com/solutions/procurement-intelligence/mtr-automation)). Third-party pricing: $100–$5,000 per month ([testcert.co comparison](https://testcert.co/compare/best-mtr-software)) [V]. |
| **Lastrev, Reducto cookbook** | PO requirements [V]. | CoC, mill cert, packing list [V]. | Heat and lot to ERP receipt [V]. | Before stock release [V]. | Reducto publishes a buildable recipe ([Reducto](https://reducto.ai/cookbooks/aerospace-receiving-certificates)) [F]. **This is evidence that the core matching step can be cloned in days.** |
| **Golden-thread tools** (Morta, Onetrace, Zutec and others) | Varies [V]. | Product evidence and change control [V]. | Asset, room, level [V]. | Gateway 3 pack [V]. | No software is prescribed ([CLC guidance](https://www.constructionleadershipcouncil.co.uk/wp-content/uploads/2024/08/CLC-Golden-Thread-Guidance.pdf)) [F]. Many vendors exist. |
| **Pay-app tools** (Siteline, Textura, GCPay) | No. | Waiver form and amount checks [V]. | Schedule-of-values line [F]. | Before GC approval [V]. | Billing compliance, not technical compliance ([Siteline–Textura](https://support.siteline.com/en/articles/14647278-siteline-textura-overview)). |

### 2.2 The manual baseline, which is the real competitor

- **Spreadsheet plus reviewer.** A DOT district materials coordinator or a contractor's QC manager keeps an item-by-item materials log and reviews it at intervals. WisDOT got its 49% lead-time cut by *moving that review earlier*, using new fields in its Materials Tracking System and training ([WisDOT](https://wisconsindot.gov/Documents/about-wisdot/performance/lean-gvmt/dtsd-materialcert-final6.pdf)) [F]. A disciplined reviewer with a good log captures much of the value.
- **ERP and QMS.** In industrial and aerospace settings, receiving holds material until acceptance is recorded ([SimpleManufacturing](https://www.simplemanufacturing.com/as9100-erp-software/)) [V]. That is a status gate, not a content check.
- **Experienced reviewer.** Content review of a mill cert takes a trained person minutes, not hours. The cost is attention and consistency across thousands of documents, not expertise per document [H].

### 2.3 Where incumbents could add the feature easily

- **AASHTOWare** could add AI reading of attachments. AASHTO's product development, however, runs through member-agency task forces and multi-year release cycles. Wisconsin is only piloting AASHTOWare materials in 2026, with implementation in 2027–28 ([WisDOT AWP KB](https://awpkb.dot.wi.gov/Content/awp-sysinfo/awp-basics/Introduction.htm)) [F]. That leaves a window, but a closing one.
- **HaulHub** owns structured delivery data and agency relationships. It is the most dangerous incumbent for a delivery-to-acceptance product [H].
- **Procore** could extend its submittal agent to delivery and installation evidence, but Procore is weak in DOT-owner workflows [H].

**What would make a new product worth buying:** it would need to sit *across* these systems. It would reconcile the approved product, delivered ticket, certificate content and tested quantity per contract item, and produce a closeout-ready exceptions list in the agency's own format. None of the tools above document doing all four together [U, not a proven gap].

---

## 3. Data access and technical feasibility: top three

### 3.1 US federal-aid highway materials certification readiness

- **Requirements data**
  - State standard specifications, special provisions, sampling-frequency guides (the FDOT Job Guide Schedule, for example) and QPLs are **publicly downloadable**. West Virginia publishes a searchable pre-approved materials database [F].
  - **Reuse rights vary by state** [U]. Each state's copyright terms need checking, but agencies generally want contractors to use these documents.
  - AASHTO and ASTM test methods are **paywalled**. ASTM's AI policy prohibits putting ASTM standards into AI tools ([ASTM AI Policy](https://www.astm.org/v3/assets/blt5eb0a2cb04534832/blta83f3cda19931cb2/67b2ea96ee5a890dc40c91ef/ASTM_AI_Policy.pdf)) [F]. **Design around it.** The acceptance limits a checker needs, such as grade, strength or gradation bands, are restated in state specifications. Reference the method by number and never ingest its text.
- **Evidence data**
  - Contractors own their POs, supplier certs and tickets, and get them at delivery. Agencies own sample and test records in AASHTOWare. A contractor can usually see the status of its own contract's materials [U, per state].
  - A pilot can run on a contractor's *own* closed-project files plus the agency's final materials deficiency letter.
  - Public records requests can also yield closed-project materials files [H].
- **Ground truth**
  - Final materials review exception lists or deficiency letters.
  - Signed materials certificates with listed exceptions.
  - Price adjustments for nonconforming material.
  - Records of materials declared non-participating.
  - **Metric:** run the tool on the project file as of each monthly estimate and measure how many of the eventual closeout exceptions it would have flagged, and how early. False alarms are flags a reviewer rejects.
- **Verification design**
  - *AI extracts:* cert type, producer, grade, heat or lot, quantities, dates and signatures, from scans and photos of tickets.
  - *Explicit rules verify:* spec limits, QPL membership, Buy America presence, sampling frequency against reported quantity, and the cert type each material requires. NCDOT's rule that brochures are not certifications is one example.
  - *Humans decide:* whether the material is accepted, field-test interpretation, substitutions, and price adjustments. **The tool never marks anything "accepted"**. It marks "evidence complete" or "evidence gap: reason".
  - *Conflicting revisions:* every requirement row carries its source document, revision and effective date. When a special provision supersedes a standard specification, the newer one wins only if it is in the contract's revision list. Anything ambiguous is shown as a conflict, never resolved silently.
  - *Approved substitutions:* a substitution needs a linked approval record. Without one, any mismatch with the approved product is flagged.
  - *Missing evidence:* evidence is reported as present, missing or unreadable. It is never inferred.
  - *Ambiguous matches:* a match is proposed only above a confidence threshold, and otherwise goes to a review queue that shows both documents side by side.
- **Deployment barriers**
  - AASHTOWare integration means agency permission and is slow, so start from document export or a contractor's own files.
  - Data sensitivity is moderate: public works records, often obtainable by records request.
  - Liability is low if the product only reports *evidence gaps* and never accepts material.
  - **A false pass** means a missed gap is still caught by the agency review, so the cost is lost trust.
  - **A false alarm** wastes reviewer time, so precision matters more than in safety domains.

### 3.2 Energy and industrial EPC: alloy piping MTR, heat traceability and turnover dossier

- **Requirements:**
  - The project piping specification and material requisitions are customer-owned and confidential.
  - ASME and API standards are licensed, with AI reuse restricted or unclear [U].
- **Evidence:**
  - MTRs (EN 10204 3.1/3.2), PMI readings, heat-marked isometrics and vendor data books.
  - These arrive at delivery and fabrication. Turnover dossiers are often assembled by hand from transferred heat numbers ([eng-tips thread](https://www.eng-tips.com/viewthread.cfm?qid=446594)) [F].
- **Ground truth:** non-conformance reports (NCRs) for wrong material, PMI rejects, dossier review comments from the owner.
- **Verification:** AI reads MTRs, and rules check chemistry and mechanical properties against the specification. PMI by XRF cannot confirm carbon ([fabrico](https://www.fabrico.io/blog/positive-material-identification/)) [F], so carbon-sensitive grades need lab or OES checks. A qualified inspector signs.
- **Barriers:** heavy competition (§2.1), confidential owner specifications, and enterprise sales to EPCs. Hexagon Smart Materials already runs check-in against POs at site ([projectmaterials blog](https://blog.projectmaterials.com/epc-projects/software/smartplant-materials)) [F, third-party].

### 3.3 Aerospace MRO and distribution: receiving release documentation

- **Requirements:** POs, customer quality clauses (Boeing X31764 is public) [F], and AS9100/AS9102, which are paywalled through SAE and IAQG.
- **Evidence:** 8130-3 or EASA Form 1, CoC and traceability chains. These are owned by the distributor or MRO, and **ITAR and export controls may apply**.
- **Public ground truth:** EASA's AOG Technics page lists affected parts and serials ([EASA](https://www.easa.europa.eu/en/domains/aircraft-products/suspected-unapproved-parts/aircraft-parts-distributed-aog-technics)) [F]. Internal quarantine and rejection records are the real ground truth.
- **Verification limit:** forged documents can be *internally consistent*. AOG Technics' paperwork looked valid, and the titanium certificates passed for about five years. **Document checking cannot detect good forgeries.** That needs an issuer-side registry or source verification.
- **Barriers:** high liability, AS9100 auditors' acceptance of software records is unknown [U], and competitors include Certivo, Lastrev and Net-Inspect.

### 3.4 Verified public datasets

| Dataset | What it contains | Use |
|---|---|---|
| [FDA Inspection Observations](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/inspection-references/inspection-observations) | Annual Excel files, FY2022–FY2025, counting 483 citations by area of regulation. FDA says it is not a comprehensive listing [F]. | Sizing purchasing-control pain in medical devices. Not usable as document-level ground truth. |
| [FDA Data Dashboard](https://datadashboard.fda.gov/) | Inspections, warning letters, seizures and injunctions, exportable and refreshed weekly [F]. | Same. |
| [BSR building control approval data](https://www.gov.uk/government/publications/building-safety-regulator-building-control-approval-application-data-may-to-july-2026/building-safety-regulator-building-control-approval-application-data-may-to-july-2026) | Gateway 2 and 3 applications received and determined, approval rates and median times [F]. | Timing the UK opportunity. |
| [EASA AOG Technics SUP page](https://www.easa.europa.eu/en/domains/aircraft-products/suspected-unapproved-parts/aircraft-parts-distributed-aog-technics) | Affected part information from the forged-certificate case [F]. | Example red-flag patterns only. |
| [Ghana Audit Service reports](https://audit.gov.gh/) | Performance and financial audits, including road works with lab test tables (Appendix 4 of the 2019 report) [F]. | Interview prompts. Grounds the Ghana payment-validation pain. |
| State DOT standard specifications and QPLs, for example [WVDOH](https://webapps.transportation.wv.gov/TWS/WVDOTDocumentStorageMigration/PDF/Transportation/highways/mcst/Material%20Procedures/2022%20MPs/106.00.04-22.pdf) | Requirements and approved products [F]. | The requirements side of the US MVP. |

**No public dataset pairs real certificates with the signed acceptance outcome.** Ground truth must come from pilot partners. This is the main data risk.

---

## 4. Who pays, and is it big enough

### 4.1 Roles

| Workflow | Daily user | Budget owner | Purchase decision | Who bears the cost of mistakes |
|---|---|---|---|---|
| US highway materials certification | Contractor QC manager or project engineer; CEI inspector | Contractor operations VP; CEI project manager | Contractor CFO or COO; CEI principal | **Contractor**, through delayed final payment and retention. **Agency**, through federal non-participation [U: exact non-participation triggers per 23 CFR 635.410 need confirming]. |
| EPC piping traceability | QC inspector, document controller | EPC project quality manager | EPC procurement or IT | EPC (rework, schedule) and owner (process safety) |
| Aerospace receiving | Receiving inspector | Quality director | Quality director plus IT | OEM and operator (safety, fleet inspections); distributor (liability) |

### 4.2 Evidence of spend and loss

- **Construction rework:** GIRI measures direct avoidable-error cost at about 5% of project value and total cost at up to 21% ([CITB](https://www.citb.co.uk/about-citb/news-events-and-blogs/getting-things-right-first-time)) [F, industry-body estimate]. Most of this is design and workmanship error, not material documentation.
- **Closeout delay:** WisDOT saved 900 staff hours per year after its fix [F]. At an assumed $80 per hour loaded cost [E], that is only about $72k per year for a whole state. **The labour-saving ROI for an agency is weak.** The money is in cash timing and avoided disallowances.
- **Ghana:** GH¢38.19m interest on three projects, and billions in disallowed arrears [F]. These are *payment-validation* losses.

### 4.3 Bottom-up size, US highway contractor and CEI wedge [E, all unverified assumptions]

| Assumption | Value | Basis |
|---|---|---|
| Federal-aid and state-funded contracts closing per year across the US | 20,000–35,000 | [E] About 45 DOTs × 400–800 lettings per year. Verify from FHWA FMIS or DOT letting reports. |
| Share with enough materials complexity to matter (bridges, structures, larger paving) | 30–50% | [E] |
| Price per contract for a readiness check | $1,500–$5,000 | [E] Anchored to the cash-timing value below. |
| **Serviceable market** | **about $9M–$87M per year** | Product of the three rows above. |
| Contractor cash-timing value per $10M contract | $8k–$20k | [E] 2–5% of contract value held to closeout × 6 months × 8% cost of capital. Retention practice varies by DOT [U]. |

**Verdict on size.** It is a viable niche software business, but not venture-scale on its own. It becomes larger only if it expands from closeout readiness to continuous acceptance tracking for contractors across all public owners, then into EPC and building work. Treat expansion as a hypothesis [H].

### 4.4 Ghana compared with the US and UK

| Factor | Ghana / West Africa | US state DOT ecosystem | UK HRB |
|---|---|---|---|
| **Customer access** | Good if founder-networked [H]: GHA, Department of Urban Roads, supervising consultants, contractor associations. | Medium. DOTs are hard. Contractors and CEIs are reachable through AGC and ARTBA chapters. | Medium. Tier 1 contractors and building safety managers. |
| **Public project records** | Auditor-General reports are rich. GHANEPS has been mandatory, with payments tied to it through GIFMIS ([PPA](https://ppa.gov.gh/mandatory-use-of-the-ghana-electronic-procurement-system-ghaneps-for-all-government-procurement/)) [F]. Project-level test records are not public [U]. | Very rich: specifications, manuals, QPLs, AASHTOWare guides, FHWA reports. | BSR statistics are public, project evidence is not. |
| **Current software use** | Low. Consultant BIM adoption was 7% in a 2016 KNUST study ([KNUST](https://ir.knust.edu.gh/handle/123456789/10181)) [F, dated]. | High: AASHTOWare, HaulHub, MetaField, Procore. | High: golden-thread platforms. |
| **Procurement barriers** | Public Procurement Act 663/914, cash constraints, and payment arrears to contractors. | DOT procurement is slow; private contractor purchase is fast. | Private contractor purchase. |
| **Timing** | Arrears validation is active now (2025–26) [F]. | Steady state. Closeout pain is chronic. | **Too early.** In July–September 2026 BSR determined only nine Gateway 3 applications, and none were active new-builds that had passed Gateway 2 ([BCIS](https://www.bcis.co.uk/news/latest-building-control-approval-application-data/)) [F]. |

**Ghana interview questions** to turn the unknowns into evidence:
- What evidence must accompany an IPC, and who checks it?
- How often is an IPC returned, and why?
- Where are material test reports filed, and on paper or electronically?
- Who in GHA or the Department of Urban Roads would pay for faster IPC validation, and from which budget line?
- Do supervising consultants' contracts reward faster certification?
- How is substandard rebar detected on site today, given the GSA's own concerns about iron rods sold without proper specifications ([AllAfrica, Jun 2025](https://allafrica.com/stories/202506180642.html)) [F]?

---

## 5. Decision

### 5.1 Ranked opportunity table

**Weights:** pain 20, buyer urgency 15, willingness to pay 15, data access 15, frequency 10, competitive intensity 10 (5 = little competition), time to pilot 10, liability 5 (5 = low liability). Scores run 1–5. The weighted total is out of 5.

| Score rank | Workflow | Pain | Freq | Urgency | WTP | Data | Compet. | Pilot time | Liability | **Weighted** | Recommended entry order | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | US highway materials certification readiness (contractor/CEI) | 4 | 4 | 3 | 3 | 4 | 3 | 4 | 4 | **3.60** | **1st** | Medium-low |
| 2 | Aerospace MRO and distribution receiving release | 5 | 5 | 4 | 4 | 2 | 2 | 2 | 1 | **3.45** | 4th\* | Medium |
| 3 | Ghana road IPC evidence validation | 4 | 4 | 4 | 2 | 2 | 5 | 3 | 4 | **3.40** | Discovery track\*\* | Low |
| 4 | EPC alloy piping MTR, heat and turnover | 4 | 5 | 4 | 4 | 2 | 1 | 3 | 2 | **3.30** | 2nd (expansion) | Medium |
| 5 | UK HRB Gateway 3 installed-product evidence | 4 | 2 | 4 | 4 | 2 | 2 | 2 | 3 | **3.05** | 3rd (from 2027–28) | Low (timing) |
| 6 | Automotive incoming / PPAP | 3 | 5 | 3 | 3 | 2 | 2 | 3 | 3 | **2.95** | Not now | Low |
| 7 | Medical device incoming acceptance | 3 | 4 | 3 | 3 | 2 | 3 | 2 | 2 | **2.80** | Not now | Medium |
| 8 | Nuclear commercial-grade dedication | 4 | 2 | 3 | 4 | 1 | 4 | 1 | 1 | **2.75** | Not now | Low |
| 9 | Rail product acceptance (UK) | 2 | 1 | 2 | 2 | 3 | 4 | 2 | 3 | **2.30** | Not now | Medium |

\*Aerospace scores second on paper, but I place it fourth for entry for two reasons. Document checks cannot catch the forgeries that drive the pain, and liability and slow pilots make it a poor *first* market. EPC comes ahead of it as the natural expansion, because the same evidence graph (cert to PO to heat to location) applies with lower liability.
\*\*The Ghana score depends on the payer. Willingness to pay is low because public owners owe contractors money. It is the best place for *discovery* but not for revenue first.

### 5.2 Three deep dives

**A. US highway materials certification readiness**
- **Workflow:** for each contract item, the product reconciles the approved source or QPL entry, the delivered tickets, the certificate content and the tested quantity against the specification and sampling guide. It produces a monthly evidence-gap list and a pre-closeout package.
- **Competitors:** AASHTOWare (quantity and status rules), HaulHub (tickets), MetaField (lab data), and manual logs.
- **Evidence of pain:** WisDOT lead times, KTC research, FHWA local-agency review, and the OIG's February 2025 finding that FHWA lacks adequate guidance for QA oversight, with 13 recommendations ([DOT OIG](https://www.oig.dot.gov/library-item/46645)) [F].
- **Strongest argument against:** WisDOT halved the delay with process changes and its existing system. AASHTOWare could add AI reading of attachments. The labour savings are small. **If contractors do not feel the cash cost, nobody pays.**

**B. EPC alloy piping MTR, heat number and turnover**
- **Workflow:** compare the MTR against the piping class, PO and heat marking, track the heat through spools and isometrics, and assemble the dossier.
- **Competitors:** MTR.AI, TestCert, Pathnovo, aekam, Certivo, Hexagon Smart Materials, SPOOLMAN/ERMAN, and Kissflow apps.
- **Evidence of pain:** CSB PMI recommendations and the 1–3% substitution estimate [F, secondary]. Vendor data sits on the critical path [F, dated].
- **Strongest argument against:** at least five funded or shipping point solutions exist, and the Reducto recipe shows the core can be cloned. A newcomer would compete on price against tools at $100–$500 per month [V].

**C. Aerospace receiving release documentation**
- **Workflow:** check that the CoC, 8130-3 or Form 1 match the PO (part number, revision, lot, approved processor) before stock release.
- **Competitors:** Certivo, Lastrev, Net-Inspect, ERP receiving modules, and the Reducto recipe.
- **Evidence of pain:** AOG Technics, Spirit titanium, and the FAA's March 2024 audit, in which 7 of 13 product audits at Spirit failed ([Manufacturing Dive](https://www.manufacturingdive.com/news/boeing-spirit-aerosystems-failed-manufacturing-safety-standards-faa-audit/709315/)) [F].
- **Strongest argument against:** the costly failures involved *well-forged* documents, which content checks pass. The real fix is issuer verification, meaning OEM-side authentication. That is a network product, not a startup's first document checker.

### 5.3 Recommended starting workflow (conditional go)

- **First buyer:** a mid-size heavy-civil contractor of about $100M–$1B in revenue doing federal-aid DOT work in one AASHTOWare state. The decision-maker is the VP of operations or the CFO. The daily user is the QC manager or project engineer. An alternative first buyer is a CEI consultant holding district inspection contracts.
- **Buying trigger:** a project stuck in closeout with final payment or retention held for materials documentation. A materials deficiency letter or a federal non-participation threat would also trigger a purchase.
- **MVP:**
  1. Ingest the contract item list, the state specification sections and the sampling-frequency guide for the items in scope. Start with 5–10 material types: rebar, structural steel, HMA, PCC, aggregate, pipe, guardrail.
  2. Ingest the contractor's tickets, certs, Buy America certs and test results, plus the agency's materials status export if available.
  3. Produce a per-item evidence matrix showing *present, missing, mismatched or unreadable*, with source citations.
  4. Generate a monthly gap report and a closeout package in the state's format.
  5. Never mark anything as accepted.
- **Documents needed for the pilot:** two or three *closed* projects, each with the full materials file, the final materials review exceptions, the date timeline from substantial completion to materials certification to final payment, and the applicable spec book edition.
- **Shadow test:** first a retrospective replay. Run the tool on the file as it stood month by month and compare its flags with the agency's final exceptions. Then run it in parallel on one live project, where the QC manager reviews flags weekly and logs whether each was real.

### 5.4 Thirty-day validation plan

**Week 1: targets and recruiting**
- 8 heavy-civil contractors: QC managers, project managers and CFOs in Wisconsin, Indiana, Montana and one more state. Recruit through state AGC and transportation builders' associations.
- 4 CEI firms: inspection managers.
- 4 DOT district materials coordinators or materials engineers: the agency view.
- 2 local public agency (LPA) federal-aid programme managers.
- 5 Ghana contacts: a GHA resident engineer, two supervising consultants, and two road contractors. This tests the IPC-validation hypothesis in parallel.

**Weeks 1–2: questions**
1. Walk me through your last project that waited more than 90 days for materials certification. What was missing, and who found it?
2. Of the closeout materials exceptions, what share were document errors, such as a wrong cert type, mismatched grade or missing Buy America cert, versus missing tests or quantity shortfalls?
3. How much money was held, and for how long? Was it retention, the final estimate or price adjustments?
4. Who keeps the materials log today, in what tool, and how many hours a month does it take?
5. What can you see in the agency's materials system for your contract?
6. Would you send us a closed project's materials file under an NDA?
7. What would a tool that cut closeout by 60 days be worth per project? Who would sign for it?
8. **Ghana only:** what documents support an IPC, why are IPCs returned, and how long does each validation step take?

**Weeks 3–4: pilot proposal**
- Free retrospective analysis on two closed projects in exchange for the files and the final exception list. Deliver a findings report.
- Offer a paid parallel run on one live project at a fixed fee of about $2,500 [E] to test willingness to pay.

**Success metrics**
- At least 10 of 18 US interviewees rank materials documentation among their top three closeout delays.
- At least two partners hand over closed-project files.
- **Retrospective recall:** the tool flags at least 70% of the agency's final exceptions at least 60 days before substantial completion, with precision of 50% or better.
- At least one contractor agrees to a paid parallel run.

**Drop or change criteria**
- Most exceptions turn out to be missing tests, staff backlog or agency sequencing. Pivot to a workflow or scheduling tool, or stop.
- Contractors say the agency bears the cost and they do not care. Test CEI firms and LPAs instead. If they also decline, stop.
- No partner will share files within 30 days. The data moat is unreachable, so stop.
- HaulHub or AASHTOWare already offers attachment reading in the target states. Narrow to non-AASHTOWare owners or stop.
- If Ghana interviews show IPC validation is acute *and* a funded payer exists, such as a donor-funded programme or the Ministry of Finance, open a separate Ghana track. Otherwise keep Ghana as a later market.

### 5.5 Cross-industry platform verdict

- **Genuinely reusable:** document ingestion and OCR for scans and photos; field extraction for certificates and tickets; the requirement–evidence graph of requirement, source, revision, evidence, match and status; citation-backed exception reports; review queues; and the audit log.
- **Industry-specific:** the acceptance *rules*, such as DOT sampling frequencies, ASME piping classes and airworthiness release rules. Also industry-specific are document taxonomies, sign-off authority, integrations (AASHTOWare, HaulHub, ERP, eQMS) and standards licensing. Buyer and sales motion differ completely by industry.
- **Evidence that would justify expansion:**
  1. At least five paying customers in the first workflow with renewal.
  2. Shown recall above 80% on retrospective ground truth.
  3. A customer pulling the product into a second document type unprompted, for example a contractor asking for it on private building or EPC work.
  4. A rules-authoring cost per new material type below an agreed threshold, showing the rule layer scales.
- **Verdict:** build a horizontal *engine* but sell a vertical *product*. Do not market a cross-industry platform until the rule-authoring cost per new domain is measured.

---

## The single most important assumption to test before writing code

**That a large share of the materials deficiencies holding up closeout and payment are errors detectable from documents already in the project file, early enough to fix, and that a party who loses money from the delay will pay to find them.** Wisconsin's 49% process-only improvement is evidence the problem may be mostly workflow, not detection. Settle it with the agency's final exception lists from two or three closed projects before building anything.

---

## Update, 8 November 2026: standards licensing decision

- **Decision:** the MVP includes a licence-gated standards library covering ISO, ASTM, BSI and GSA. Licences will be negotiated after the proposal is accepted.
- **Behaviour until each licence is signed:** that publisher's limits are entered by hand, keeping only the numbers and clause references. AI extraction runs only on the Ghana road specification and contract documents, used with the client's permission.
- **Constraints confirmed:**
  - ISO's licence bans AI processing unless ISO, a member body or a distributor grants a separate licence ([ISO terms](https://www.iso.org/terms-conditions-licence-agreement.html)).
  - ASTM bans AI use, even by licensees, without written permission from its President ([ASTM AI policy](https://store.astm.org/media/wysiwyg/ASTM_AI_Policy.pdf)).
  - BSI's and GSA's AI terms were not found [U].
- **Negotiation order:** GSA, then ISO through GSA, then BSI, then ASTM.
- **Full design:** the standards library section of [../docs/architecture.html](../docs/architecture.html).
