# Proposed draft PR: Add BuildExchange procurement, equipment rentals and site receipt demo

Adds a self-contained Django/DRF application under `buildexchange/` for construction procurement and general equipment rentals. A purchaser can order from multiple suppliers; transporters record custody checkpoints; the assigned site supervisor reconciles quantities/conditions and signs a timestamped receipt with protected optional photo evidence. Arrival and payment records remain separate from receipt confirmation.

Includes supplier/purchaser/transporter/supervisor/admin workspaces, audited manual payment/deposit/refund records, rental time-range availability and return inspection, migrations, fictional seed accounts, tests and local VS Code/run instructions. Existing local Yebbo source is retained; no legacy database migration or synchronization is attempted.

Validation: see BUILDEXCHANGE-VALIDATION.md for executed checks and limits. PostgreSQL concurrency, hosted operation and real integrations remain outside current evidence. Source blueprint inspection and attribution decisions are in BUILDEXCHANGE-BLUEPRINTS.md.

Integration note: local main starts at 6d7bb311dc01c5241b64887adda7077a34c66072; the pre-existing Yebbo application was uncommitted local work and is included in the isolated source copy. Review that inherited source separately. Connected GitHub access returned 404 for moonxight/yebbo, so this file is a proposed description, not an opened PR.
