# Add an operational construction-marketplace prototype

The initial BuildExchange demo exposed internal audit data in customer views and relied on support administrators for manual payment records. This update introduces role-specific buyer, supplier, transporter, site-receiving and customer-support workspaces, with a local bank simulator that records approval, decline, retry, fictitious debits and refunds.

Adds six research-based Zambia storefronts, 37 catalogue samples, source/price/hour provenance, original brand artwork and a blue/amber responsive interface. Buyers choose a site pin and see server-derived delivery, labour and platform fees before checkout. Transporters can explicitly share device GPS or run a labelled coordinate rehearsal; OpenFreeMap/MapLibre displays persisted positions and recipient refresh. Arrival remains separate from supervisor inspection and receipt.

Support is restricted to submitted cases and their relevant order details, with no shopping, dispatch, catalogue, banking or account-provisioning powers. Includes additive migrations, repeatable source seeding, prototype terms and updated demonstration/asset/source documentation. Rentals pay charge plus deposit in the simulator, returning only the deposit after inspection or the full amount on uncollected cancellation.

Validation: 36 SQLite workflow/integration tests passed; system, migration and JavaScript checks passed. Browser demonstration covered map-selected checkout, payment, supplier/driver custody, simulated movement, receipt and support response. Physical phone GPS, PostgreSQL concurrency and hosted/live-provider integrations remain unverified. See BUILDEXCHANGE-V2-VALIDATION.md for boundaries.

No supplier or bank integration/affiliation is claimed. Prices, stock, map pins, fees and ETA are labelled by evidence basis. The inherited Yebbo source snapshot remains a separate commit. No remote push or PR has been performed by this local update.
