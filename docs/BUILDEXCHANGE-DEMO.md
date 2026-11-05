# Classroom demo and local run

Open `BuildExchange-ZM.code-workspace` in VS Code. Open a terminal in `buildexchange/`.

Windows PowerShell, Python 3.13 recommended:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

On macOS/Linux use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows interpreter path. Alternatively double-click `Start BuildExchange.cmd` in the project root on Windows. Its first run downloads trusted PyPI dependencies. If `venv` cannot bootstrap pip on this PC, use the installed system pip: `python -m pip --python .venv/Scripts/python.exe install -r requirements.txt`.

Open `http://127.0.0.1:8000/`. Demo password is `BuildDemo2026!` unless DEMO_PASSWORD was set before account creation. All data and names are fictional. Seed reruns do not overwrite passwords, stock or orders.

| Account | Role |
| --- | --- |
| buyer | Purchaser |
| supplier / supplier2 | Two independent suppliers and equipment owners |
| driver / driver2 | Independent transporters |
| supervisor / supervisor2 | Site supervisors |
| admin | Operations administrator |

## Procurement → custody → discrepancy receipt

1. Sign in as buyer. Add 10 cement bags and optionally sheets from supplier2. Checkout with a fictional site and supervisor. Separate supplier orders appear; prices/stock are server checked.
2. Optionally request a quotation from a sale listing. Sign in as that supplier to offer a unit price in integer ngwee; buyer can accept the offer into an order. This is a separate route from cart checkout, so do not accidentally order twice during the presentation.
3. Sign in as supplier. Open Orders & tracking, Accept order, then Ready for collection. For a supplier2 order, use supplier2.
4. Sign in as driver. Open Open delivery jobs, accept the job. In Orders & tracking record pickup, in transit and arrived in sequence with notes. Choose Status only, or explicitly consent to a clearly labelled demo location. Arrival leaves the order awaiting supervisor inspection.
5. Sign in as supervisor. Open Site reconciliation. Count 8 of the 10 bags, select Good and explain two missing bags. Optionally attach a nonsensitive sample inspection photo. Confirm inspection and sign. The order becomes DISPUTED. A full good delivery would become RECEIVED.
6. Open the printable receipt: ordered versus received, actor/time, notes, optional evidence and event trail. Use the browser's print/save PDF function if desired. This is an account-authenticated record, not legal signature certification.
7. Buyer and supplier can see the receipt and exchange order messages. Another supervisor cannot access it. Admin can record a manual payment reference separately; the workflow moves no money.

## General equipment rental

1. As buyer expand a generator/pump/power-tool listing, choose a future start and end, and check availability. Book; the server checks again in a transaction. Booking the entire fleet prevents an overlapping booking; adjacent end/start times can be booked.
2. As admin open Rental bookings and record the fictional deposit reference. This does not transfer funds.
3. Within the booked time range, supplier2 (generator/pump) or supplier (drill) records equipment collection. Collection before the range or without a required deposit record is rejected. For a quick demo choose a start one minute ahead, then wait until that time.
4. Supplier records inspected return and condition. The deposit becomes REFUND_PENDING. Admin records a separate manual refund reference. Uncollected bookings can be cancelled by their purchaser, releasing capacity.

## PostgreSQL option

Create a dedicated local PostgreSQL database/user with permission to create a test database if running tests. Copy `.env.example` to `.env` and set DB_ENGINE=postgres plus your local POSTGRES_* values. Run migrate and seed_demo again for that separate database. Do not point these commands at a shared or production database. SQLite records are not automatically copied to PostgreSQL. PostgreSQL execution has not been verified on this PC because the Docker engine was unavailable.

## Verification

```powershell
.venv\Scripts\python.exe manage.py test exchange
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Optional dependency check: install pip-audit into the virtual environment and run `python -m pip_audit -r requirements.txt --no-deps --disable-pip`. Requirements pin the complete small runtime dependency set; rerun audit before any future use. Do not run the legacy Yebbo launcher when demonstrating this application: it serves a separate grocery marketplace and database.

Stop the server with Ctrl+C. To create a clean rehearsal, stop it, rename `demo.sqlite3` to a dated backup (do not delete it), and rerun migrate/seed_demo. Back up `private-media/` with its corresponding database if it contains receipt evidence.
