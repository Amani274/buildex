# BuildExchange ZM — functional local student demo

Construction procurement, general equipment rentals and site delivery reconciliation. Open `BuildExchange-ZM.code-workspace` in VS Code, or use **Start BuildExchange.cmd** on Windows.

The new application is in **buildexchange/**: Python, Django, Django REST Framework, PostgreSQL configuration and a tested SQLite demo option. Existing local Yebbo TypeScript/Express/React/Expo source is preserved alongside it; it is a separate grocery-marketplace application with separate data.

## Run locally

From `buildexchange/`:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/. Accounts: `buyer`, `supplier`, `supplier2`, `driver`, `supervisor`, `admin`. Default fictional demo password: `BuildDemo2026!`. Use Python 3.13. See [full setup and demo script](docs/BUILDEXCHANGE-DEMO.md), including pip bootstrap recovery and PostgreSQL configuration. Seeding is repeatable without resetting records.

## Working features

- Verified role workspaces; administrator account provisioning, verification and suspension.
- Supplier-owned construction material/equipment sale listings and general equipment rentals.
- Multi-supplier cart, per-supplier checkout, atomic stock reservations and negotiated quotations.
- Manual payment and refund records with references; no money moves.
- Third-party transporter job acceptance, pickup/status checkpoints and optional consented/demo coordinates.
- Assigned site supervisor inspects every ordered line, records quantity/condition/shortages and signs one timestamped receipt.
- Protected optional photo evidence, printable receipts, order communications and actor/time event history.
- Time-range rental availability, booking, separate deposit record, collection, inspected return and manual refund bookkeeping.

## Project evidence and handoff

- [Architecture, source provenance and permission boundaries](docs/BUILDEXCHANGE-ARCHITECTURE.md)
- [Executed validation and limitations](docs/BUILDEXCHANGE-VALIDATION.md)
- [Blueprint inspection, security review and attributions](docs/BUILDEXCHANGE-BLUEPRINTS.md)
- [Four business questions](docs/BUILDEXCHANGE-BUSINESS.md)
- [API operations](docs/BUILDEXCHANGE-API.md)
- [Remaining work and team completion map](docs/BUILDEXCHANGE-REMAINING.md)
- [Proposed draft PR description](docs/BUILDEXCHANGE-DRAFT-PR.md)

Local branch: `feature/buildexchange-zm`, based on the verified local yebbo history. The original/default branch and original checkout are unchanged. GitHub access for `moonxight/yebbo` returned 404 through the connected `tap310` account, so remote state/push rights remain unverified and no PR was opened. The inherited local Yebbo application was uncommitted work; it is preserved in this separate copy and identified in the provenance notes.

This is a local classroom demo. No live payment gateway, automated GPS, mobile-store build, production hosting, commercial traction or dispute adjudication is claimed. PostgreSQL runtime/concurrency validation and pilot operational/privacy work remain. All sample prices and names are fictional.
