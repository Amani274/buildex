> Historical v1 document. The current operational prototype is described in [BUILDEXCHANGE-V2-GUIDE.md](BUILDEXCHANGE-V2-GUIDE.md), with current roles, bank simulation, fees, maps and validation.

# Completion map for classmates

Implemented and tested locally: role verification, supplier-owned sale/rental listings, quote negotiation, multi-supplier cart checkout, stock reservations, per-supplier orders, manual payment/refund records, transporter job claims and checkpoints, explicit location consent/source labels, supervisor-only line reconciliation, discrepancy receipts, private photo evidence, printable receipts, rental availability/bookings/deposits/collection/returns/refunds, order messages and read-only audit history.

| Next work | Suggested owner / completion evidence |
| --- | --- |
| Remote integration | Repository maintainer: grant connected access, inspect current remote main, reconcile this branch, push feature branch and open draft PR; never force-push main |
| PostgreSQL verification | Backend lead: run migrations and tests on isolated PostgreSQL, then competing checkout/booking/claim tests with independent connections |
| Pilot discovery | Product lead: dated consenting retailer, contractor, supervisor and equipment-owner interviews; record findings without inventing respondents |
| Operational exceptions | Backend/product pair: agreed cancellation, discrepancy resolution, overdue rental, over-delivery and supplier-suspension rules with tests |
| Hosting readiness | Release lead: HTTPS, secret management, static/private media, access logging, backups/restore, login abuse protection and monitored staging tests |
| Privacy and policies | Operations lead: consent wording, retention/export/deletion procedure, identity verification, dispute responsibilities and pilot terms |
| Reliability | Frontend/backend pair: rental idempotency, bounded/paginated feeds, retry recovery, mobile device/browser checks and accessible error focus |
| External integrations | Only after separate authorization: actual payment sandbox/provider callbacks and permissioned device location; never label a demo as live |
| Assessment handoff | QA lead: run the documented demo, capture evidence, assign actual teammate names and distinguish local demo results from market outcomes |

Suggested roles are responsibilities, not claims about who has done the work. No hosting, real transactions, merchant partnerships or commercial traction is claimed.
