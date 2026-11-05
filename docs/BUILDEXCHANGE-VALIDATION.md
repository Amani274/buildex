> Historical v1 document. The current operational prototype is described in [BUILDEXCHANGE-V2-GUIDE.md](BUILDEXCHANGE-V2-GUIDE.md), with current roles, bank simulation, fees, maps and validation.

# Executed validation — 5 November 2026

## Local application

Python 3.13.15, Django 5.2.19, DRF 3.18.3, SQLite, Windows. The Python dependencies were installed from PyPI into an isolated environment outside the deliverable source. No blueprint script was executed.

**24 integration/workflow tests passed** using Django's isolated SQLite test database. Coverage includes:

- Multi-supplier checkout, supplier order splitting, stock deduction, request replay and changed-details rejection.
- Full order → supplier preparation → transporter claim/pickup/transit/arrival → supervisor discrepancy receipt; separate payment status and audit events.
- Full good receipt, duplicate signing rejection, wrong-supervisor/transporter denial, missing/duplicate receipt lines and shortage explanation.
- Atomic rollback after stock failure; other suppliers cannot update listings/orders; purchasers cannot record payments.
- Delivery claims cannot be overwritten; skipped statuses and another driver's checkpoint fail; location consent and finite-coordinate checks.
- Quote request, supplier offer, purchaser acceptance at negotiated price and repeat acceptance replay.
- Rejection restores stock once and requires separate manual payment refund bookkeeping.
- Rental overlap rejection, adjacent time ranges, peak concurrent capacity across disjoint bookings, deposit/collection/return/refund, cancellation, invalid ranges and overdue equipment blocking future availability until returned.
- Photo decoding/re-encoding, private evidence access and printable receipt; invalid image rollback.
- Admin account provisioning/verification, hashed passwords, no purchaser role escalation, session CSRF and anonymous access.
- Open-job board redaction, no generic delete mutation, role workspace payloads and login rendering.

`manage.py check` passed. `makemigrations --check --dry-run` found no drift after the committed migration files were generated. `node --check` accepted the workspace JavaScript. Git whitespace validation passed before delivery.

The Windows `Start BuildExchange.cmd` launcher was also run: it created its virtual environment, installed the pinned dependencies through system pip, applied migrations, preserved/reused the demo seed and started the loopback Django server. Its environment creation avoids this PC's failing ensurepip bootstrap.

## Browser evidence

The local application was exercised through the in-app browser using fictional demo accounts:

1. buyer added 10 cement bags and checked out at ZMW 1,600.
2. supplier saw 190 remaining bags, accepted the order and marked it ready.
3. driver saw the redacted open job, claimed it and recorded pickup, in transit and arrival with status-only notes.
4. supervisor saw the assigned arrived order, recorded 8 received, explained 2 missing bags and signed the inspection.
5. The order became DISPUTED. The printable receipt showed 10 ordered / 8 received, actor/timestamps and 8 audit events. Payment stayed PENDING.

The receipt screenshot is supplied separately as `BuildExchange-receipt-preview.png`. Browser inspection used the actual persisted local demo, not a mockup. Photo security, quotations, manual payment handling and rental lifecycle were covered by integration tests; full manual browser replay of those additional flows and physical device/accessibility checks are not claimed.

## Dependencies and source review

Final `pip-audit` check of the fully pinned small runtime set reported **no known vulnerabilities**. An initial DRF selection produced advisories and was updated before the final audit/test run. The audit result is point-in-time and cannot establish absence of vulnerabilities. See `evidence/dependency-audit.json` and BUILDEXCHANGE-BLUEPRINTS.md. Blueprint transitive dependencies and the inherited Yebbo npm runtime were not installed/audited.

## Explicit limits

- PostgreSQL runtime/concurrency remains unverified: Docker CLI was present but its Linux engine pipe was unavailable. PostgreSQL configuration and migrations are provided; no hosted/Neon database was touched.
- Local API tests and sequential browser tests do not prove concurrent PostgreSQL behavior, production scale, device support or hosted reliability.
- GitHub app identity was tap310; moonxight/yebbo metadata/contents returned 404 and push permission could not be verified. No remote push, fork, PR or deployment occurred.
- The original source checkout and local main branch remain unchanged; the isolated feature branch includes the inherited local uncommitted Yebbo application as a separately identified source snapshot.
- No live payments, automatic GPS, external messages, investor traction or legal-signature certification were tested or claimed.
