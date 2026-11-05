# Validation record

## Verified on 3 October 2026

- Root TypeScript check passed.
- Nine API integration tests passed: full cash-order lifecycle and reconciled reports; duplicate request protection; price/cart/coordinate validation; declined simulated payment and refund handling; role restrictions; promo and stock rules; support and suspended accounts; sign-out and trusted-origin checks; SQLite persistence after reopening.
- Browser application build passed.
- Native TypeScript check passed after correcting an unclosed fragment in the rider delivery screen.
- Expo export passed for Android, iOS and web. This verifies bundles, not signed installers or physical devices.
- The compiled presentation launcher successfully served the storefront on port 4000 with its own database.
- Phone layout checked at 390 pixels; introductory text and the food illustration now have separate space. Desktop preview saved in `docs/screenshots/presentation.png`.

The earlier browser rehearsal completed checkout → merchant preparation → administrator assignment → rider acceptance → pickup → cash-confirmed delivery. The classroom guide documents the same workflow and its expected totals.

## Presentation preparation

`scripts/present.mjs` serves the compiled browser application and uses a separate presentation database. `--fresh` selects a new timestamped database without deleting existing data. The compiled browser app requires no development server during the classroom demo.

## Limits

These checks verify local behaviour. They do not establish real payment processing, real dispatch, native device behaviour or store publication. Food images and web fonts load from external services, so have internet available and preload the demonstration pages.

The native export generated bundles under `apps/mobile/dist`, which is ignored by Git and can be regenerated.
