> Historical v1 document. The current operational prototype is described in [BUILDEXCHANGE-V2-GUIDE.md](BUILDEXCHANGE-V2-GUIDE.md), with current roles, bank simulation, fees, maps and validation.

# Architecture and boundaries

The source checkout on this PC identifies `https://github.com/moonxight/yebbo.git` as origin. Its local main HEAD was `6d7bb311dc01c5241b64887adda7077a34c66072`. The local TypeScript/Express/React/Expo application files were uncommitted additions on top of that planning-era history. They have been preserved in this isolated copy. The original checkout was not modified.

Connected GitHub identity: `tap310`. Installed repository searches returned no yebbo. Direct metadata and contents lookup for `moonxight/yebbo` returned 404, and collaborator permission lookup returned null. Thus current remote default branch, remote architecture and push/fork rights are unverified. Local tracking says main/origin/main; that is not proof of the current remote state. This implementation lives on local `feature/buildexchange-zm`. No remote branch, fork, push or PR is claimed.

## Stack decision

The existing local implementation serves a grocery/restaurant marketplace using Express, TypeScript and Node SQLite; customer/rider Expo and merchant/admin React views share its local API. Reusing its single-shop order model directly would require a migration to normalized rentals, per-line site inspection and different roles. The user selected Python/Django/DRF/PostgreSQL in the referenced discussion. A self-contained Django implementation in `buildexchange/` keeps a clear migration boundary and preserves the legacy source for review. No dual database synchronization is attempted.

One Django server provides session authentication, a responsive role workspace, DRF endpoints and protected media. PostgreSQL is configurable; SQLite is the tested zero-service classroom option. No Django Oscar, Channels, Celery or Redis is needed for the implemented scope. Updates are refreshed manually, avoiding claims of real-time transport integration.

## Data and critical rules

Profile verification gates business operations. Listings belong to suppliers and distinguish sale stock from total rental fleet capacity. A purchaser cart can contain multiple suppliers; checkout atomically reserves stock and creates one order per supplier. Order lines snapshot product names, units, quantities and prices. A per-purchaser checkout key replays the original order IDs rather than charging/reserving again. Reusing it with different delivery details fails; a retry of the same key refers to the original basket even if the cart later changes.

Quotes are requested per sale listing, answered by its supplier and accepted by the requesting purchaser. Acceptance reserves stock at the offered price. Quotes do not expire automatically in this demo. Orders progress PLACED → ACCEPTED → READY; a new order may be rejected and stock released once. A READY order creates an OPEN delivery job. One verified transporter can claim it by a conditional database update, then record ASSIGNED → PICKED_UP → IN_TRANSIT → ARRIVED. Coordinates are optional, require explicit consent and are labelled demo or consented-gps; the latter is a self-reported coordinate, not independently authenticated device GPS.

Only the assigned verified supervisor can reconcile an ARRIVED order. Every line must appear exactly once with quantity and condition; shortages/damage require explanation. The account-authenticated, timestamped receipt changes the order to RECEIVED or DISPUTED. It does not alter payment status. Receipt/evidence reads use order scope; there is no public media URL. Photos are optional, limited to four 2 MB images, decoded/re-encoded, metadata stripped and SHA-256 hashed. No edit/delete receipt API exists. Database administrators remain able to alter database files; this is not a tamper-proof ledger.

Rentals use half-open [start,end) intervals. Asset-row locking serializes capacity checks on PostgreSQL; SQLite uses immediate write transactions. Capacity is computed as peak concurrent units across the interval. Started 24-hour periods determine the charge; deposits are separate snapshots. Admin records deposit receipt manually; equipment supplier records collection within the booking period and an inspected return; deposit refunds need a separate manual admin entry. Equipment still collected after its due time blocks new future availability until returned. Handling conflicting pre-existing bookings, overdue charges and replacement equipment remains operational work before a real rental pilot.

Payment status is bookkeeping only: PENDING → RECORDED_MANUAL; a paid rejected order enters REFUND_PENDING and an administrator can record REFUNDED_MANUAL with a reference. Rental deposits follow the same separation. No credentials, payment SDKs, webhook claims or actual transfers are involved. Transport fees and rental-charge settlement are arranged manually; platform fee calculations are outside this demo.

## Permissions

| Role | Allowed actions |
| --- | --- |
| Purchaser | Browse verified listings, cart/checkout, request and accept own quotes, book/cancel own uncollected rentals, view own orders and receipts |
| Supplier | Create/edit own listings, answer own listing quotes, prepare/reject own orders, inspect collection/return of own equipment |
| Transporter | View redacted open jobs, accept one, see assigned order, record its pickup and checkpoints |
| Supervisor | View assigned orders, reconcile every line and sign one site receipt |
| Admin | View operational records, provision non-admin accounts, verify/suspend accounts, record manual payments/deposits/refunds, read audit trail |

All order participants can communicate in a persisted order thread. Messages have no outbound email/SMS delivery. Privileged account creation never grants admin role through the workspace. Django's built-in admin exposes a read-only audit list only; operational writes go through checked services.

## Before commercial or hosted use

Complete PostgreSQL runtime/concurrent-request validation, independent security review, backup/restore practice, HTTPS hosting and static/media serving. Add durable login abuse protection, account recovery, verified identity onboarding, privacy/retention/export/deletion procedures, monitoring and pagination. Resolve overdue equipment, supplier deactivation, order cancellation beyond rejection, over-deliveries, returns/refunds, dispute resolution and transport pricing. Evaluate signed provider callbacks and actual device tracking separately if authorized later. No deployment readiness is claimed.
