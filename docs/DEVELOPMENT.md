# Run Yebbo locally

## Requirements

- Node.js 24 or newer (the API uses Node's built-in SQLite and TypeScript support).
- pnpm 11.19.0, as pinned in package.json.
- Internet for the first dependency install and illustrative food photos. The database itself stays local.

## Start the application

From the repository root:

```sh
pnpm install
pnpm dev
```

Open http://127.0.0.1:5173. The API runs on http://127.0.0.1:4000. The first run creates `data/yebbo.sqlite`, six fictional shops, 26 products, five Lusaka delivery zones, and four development accounts.

To serve a compiled version from one port:

```sh
pnpm build
pnpm start
```

Then open http://127.0.0.1:4000. Restart the API after the first build so it discovers the compiled files.

## Demo accounts

| Account | Email | Access |
| --- | --- | --- |
| Customer | customer@yebbo.test | Shop, order, save favourites, review and request support |
| Merchant | merchant@yebbo.test | The Burger Yard menu and order queue |
| Rider | rider@yebbo.test | Assigned jobs, collection, delivery and cash confirmation |
| Administrator | admin@yebbo.test | Dispatch, reports, shops, people, zones, support and audit log |

The initial password is `YebboDemo2026!`. These are deliberately visible **local demonstration accounts**, not production credentials. Set `DEMO_PASSWORD` before the first run to override it. Changing that environment variable does not change passwords already stored in an existing database. Use the account password-change screen for existing accounts.

The demo merchant manages The Burger Yard. For other shops, create a customer account through sign-up and have an administrator assign the merchant role and shop in People & access.

## Demonstrate one complete order

1. Sign in as the customer. Add The Yard Classic from The Burger Yard.
2. Apply WELCOME10 if this account has not used it. Add fictional delivery details inside Rhodes Park, including a valid-format Zambian mobile number.
3. Choose cash or clearly labelled mobile-money simulation and place the order.
4. Sign out in Account. Sign in as merchant. Accept, start preparing, and mark ready.
5. Sign in as admin. Assign the ready order to Mwamba.
6. Sign in as rider. Accept the delivery, confirm pickup, and complete it. Cash orders require collection confirmation.
7. Return to the customer receipt/review and admin analytics. Export the report.

Use separate browser profiles or the native app for simultaneous roles. Tabs in the same browser profile share the web session cookie.

## Checks

```sh
pnpm typecheck
pnpm test
pnpm build
pnpm --dir apps/mobile typecheck
pnpm --dir apps/mobile export
```

Tests create isolated databases and do not modify the running demonstration's data. They exercise prices, discount rules, roles, dispatch, delivery, refunds, idempotency, stock and persistence.

## Data and backups

The database and credentials are ignored by Git. Stop the API before copying `data/yebbo.sqlite`, or use the included online backup command:

```sh
node scripts/backup.mjs
```

It uses SQLite's backup API and verifies integrity. The result is saved in `data/backups/`. To restore, stop the API, keep a copy of the existing database files, and copy a verified backup to the configured database path. Do not overwrite a live database or mix an old database with unrelated WAL/SHM files.

For a fresh demo, move the existing `data` folder somewhere safe while the API is stopped; the next run seeds a new database. No automatic reset deletes orders.

## Native application

See [MOBILE.md](MOBILE.md). The native customer/rider app talks to the same API. Localhost on a phone means the phone, not your computer.

## Troubleshooting

- **API not reachable:** start the API, check the port, and confirm WEB_ORIGIN includes the exact web origin.
- **Phone cannot connect:** put the phone and computer on the same trusted Wi-Fi, set HOST=0.0.0.0 in the local server environment, and configure EXPO_PUBLIC_API_URL using the computer's LAN IP.
- **Quote not available:** check shop opening status, minimum spend, stock, delivery zone and promo eligibility.
- **Old role after an access change:** sign in again. Role changes revoke sessions.
- **An item looks blank:** photographs load from Unsplash and need network access; prices and ordering remain local.
- **pnpm tries to reinstall when changing OS users:** use the same user for install and run, or run the underlying Node scripts directly. Do not delete the repository to resolve a package-cache mismatch.
