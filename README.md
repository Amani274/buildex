# BuildExchange ZM — From yard to site.

A functional local construction procurement, general equipment rental, bank-payment simulation and delivery/site-receipt prototype. Open **BuildExchange-ZM.code-workspace** in VS Code or double-click **Start BuildExchange.cmd** on Windows. The application runs at http://127.0.0.1:8000/.

## What works

- Six research-based Zambian storefronts and 37 sourced/sample catalogue entries, category/search filters, original product illustrations and full-catalogue/source links. Public price snapshots are distinguished from demo prices, stock and sample variants.
- Multi-supplier basket, map-selected site pin, server-calculated delivery/labour/platform fee breakdown, per-supplier checkout and quotations.
- Local bank simulator with illustrative bank options, fictitious account balances, approval/decline/cancel/retry, transaction receipts, duplicate-payment protection and simulated refunds. No real bank credentials or money transfers.
- Supplier order preparation; third-party driver job claims, pickup/arrival controls, opt-in device GPS and a clearly labelled moving-vehicle rehearsal. Recipient tracking refreshes while its map is open.
- Assigned supervisor quantity/condition reconciliation, discrepancies, private optional photo evidence and printable site receipts. Arrival and payment remain separate from receiving.
- Separate equipment rentals: availability/time ranges, rental-plus-deposit demo payment, collection, inspected return and deposit-only refund; an uncollected paid cancellation returns the full simulated charge.
- Buyer location and cancellation: the basket map has a **Use my current location** button (browser permission and HTTPS or localhost needed; locations outside Zambia are refused). Buyers can cancel their own order until the supplier accepts it; an unpaid order is voided and a paid one is refunded in the demo bank, and the stock is released either way.
- Customer-support workspace: cases come first when open, each with the order's status and payment state. Support can open a case from an order number and make audited repairs on a case's order: cancel and refund before a driver accepts, clear a stuck or expired bank session, change the receiving supervisor, and correct the site address. Each repair needs a reason, which is posted to the order thread. Support still cannot buy, dispatch, edit prices or catalogues, record payments or provision accounts, and sees no amounts or payment references.
- Soft navy/blue/amber visual theme, original logo and hero, feedback/loading states, reduced-motion handling and responsive layouts. Prototype terms and location/fee/source explanations are available in the application.

## Start locally

Python 3.13 recommended. The Windows launcher creates the environment through system pip (avoiding this PC's ensurepip issue), applies migrations, then runs seed_demo and seed_marketplace without resetting existing records. Internet is needed for initial dependency setup and map backgrounds.

Manual setup, from buildexchange/:

```powershell
python -m venv --without-pip .venv
python -m pip --python .venv/Scripts/python.exe install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe manage.py seed_marketplace
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Buyer: **buyer**. Suppliers: **chilanga**, **builders**, **micmar**, **lamasat**, **handymans**, **camco**. Transporter: **driver**. Site receiving: **supervisor**. Customer support: **admin**. Independent demo rental owners: supplier / supplier2. Default demo password: **BuildDemo2026!** (unless changed or set through DEMO_PASSWORD when first created). The login page provides role-selection buttons.

## Guides and evidence

- [Current workflow and demonstration guide](docs/BUILDEXCHANGE-V2-GUIDE.md)
- [Current validation and known limits](docs/BUILDEXCHANGE-V2-VALIDATION.md)
- [Supplier catalogue, pricing and hours sources](docs/BUILDEXCHANGE-SUPPLIER-SOURCES.md)
- [Brand descriptions, artwork and map licensing](docs/BUILDEXCHANGE-BRAND-ASSETS.md)
- [Business differentiation, sales, value and investors](docs/BUILDEXCHANGE-BUSINESS.md)
- [Blueprint inspection and attributions](docs/BUILDEXCHANGE-BLUEPRINTS.md)
- [Merge-later guidance](docs/BUILDEXCHANGE-MERGE-LATER.md)

Run checks from buildexchange/: `.venv\Scripts\python.exe manage.py test exchange`, `manage.py check`, and `manage.py makemigrations --check --dry-run`.

The Django/DRF application lives in buildexchange/. PostgreSQL configuration remains available in .env.example; SQLite is the verified local option. The previous Yebbo TypeScript/Express/React/Expo application is preserved separately alongside it, with its own database and launcher. The original checkout and main branch remain unchanged. Work stays on feature/buildexchange-zm; no remote push or Render deployment is claimed.

Phone GPS is implemented but physical-phone operation requires a reachable HTTPS address and explicit permission; ordinary phone-to-PC insecure LAN HTTP is insufficient. Demo movement is available for local presentations. OpenFreeMap backgrounds require internet/WebGL and have no service availability guarantee. Pins, stock, dispatch estimates, fees and most prices are demonstration assumptions. The named businesses and banks are not partners or integrations. This is a local prototype, not a commercial service.
