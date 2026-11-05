# Yebbo ✦

**Your city. Delivered.** A turquoise delivery marketplace built around Lusaka, with prices in Zambian kwacha, a native iOS/Android client, and a shared local backend.

Yebbo is an independent BIT301 student project inspired by familiar delivery apps. It has its own identity and implementation; it is not affiliated with Glovo. The working name remains Yebbo.

> **Current scope:** A functioning local development application. Shops, ratings and delivery estimates are fictional. Airtel Money and MTN MoMo are explicitly labelled simulations. No real payment, merchant dispatch, live rider GPS, public hosting or app-store release is connected.

## Run it

**Presenting in class?** Follow [the seven-minute walkthrough](docs/PRESENTATION.md). After building once, double-click **Start Yebbo.cmd**, or run `pnpm present`. Use `pnpm present:fresh` for a new rehearsal database that preserves previous work.

Install Node.js 24+ and pnpm 11.19.0, then run:

```sh
pnpm install
pnpm dev
```

Open **http://127.0.0.1:5173**. The API runs on port 4000 and automatically creates `data/yebbo.sqlite`. The database stays on your computer, as requested. No cloud account is needed.

| Perspective | Email | What to try |
| --- | --- | --- |
| Customer | customer@yebbo.test | Browse, order, follow delivery and review |
| Merchant | merchant@yebbo.test | Accept and prepare Burger Yard orders; manage its menu |
| Rider | rider@yebbo.test | Accept an assigned job, collect and deliver |
| Administrator | admin@yebbo.test | Dispatch, reports, stock, shops, people and support |

Initial local demo password: **`YebboDemo2026!`**. These accounts are intended only for development. See [the setup guide](docs/DEVELOPMENT.md) for password configuration, backups and a complete demonstration walkthrough.

## What is implemented

- **Customer storefront:** responsive turquoise design, shop/category/product search, sorting, menus, stock, favourites, saved bag, delivery details, five Lusaka zones and optional native delivery coordinates.
- **Checkout:** server-calculated prices in ngwee, minimum spend, single-shop bags, WELCOME10 eligibility, cash and simulated mobile money, persisted orders, duplicate-request protection and stock reservation.
- **Order experience:** status timeline, illustrated delivery progress, receipts, reorder, cancellation rules, post-delivery reviews and support requests. Updates refresh while the app is active.
- **Merchant workspace:** incoming orders, preparation stages, product creation and editing, stock and opening controls.
- **Rider workflow:** assigned jobs, explicit acceptance, pickup and completion; cash orders require collection confirmation. Directions open an external maps app.
- **Administrator workspace:** dispatch, merchant approval and fees, account roles/suspension, delivery zones, support replies and audit history.
- **Reports:** date-filtered orders, completion/cancellation rates, delivery duration, delivered merchandise value, merchant payable, platform revenue, shop performance and CSV export. Figures come from stored orders, not fabricated charts.
- **Account controls:** customer registration, password hashing, HTTP-only browser sessions, secure native token storage, password changes, sign-out and customer account closure with contact anonymisation.

The mobile client provides customer and rider journeys. Merchants and administrators use the responsive browser workspace. All clients share one API and database.

## iOS and Android

The Expo/React Native project lives in `apps/mobile`. It includes app icons, native screens, secure sign-in, persistent bags and EAS build profiles.

```sh
# In apps/mobile/.env, set EXPO_PUBLIC_API_URL to your computer's LAN API address.
pnpm mobile
```

Read [the mobile guide](docs/MOBILE.md) before connecting a phone. A phone cannot reach your computer using `127.0.0.1`; the API needs an explicitly configured LAN listener. Signed installers, device testing and store publication remain separate release steps requiring the relevant developer accounts. No downloadable binary is claimed yet.

## Project layout

```text
apps/dashboard/   React customer storefront and staff workspaces
apps/mobile/      Native Expo application for iOS and Android
apps/server/      Express API, SQLite persistence and integration tests
packages/shared/  Shared models, money and order status helpers
scripts/          Local startup and verified database backup
 docs/            Architecture, execution blueprint and release guidance
```

## Execution blueprint and delivery stages

The [original execution blueprint](docs/BLUEPRINT.md) is retained as the planning baseline. Its original Supabase proposal is superseded for this build by the user's decision to keep the backend local; see the [architecture](docs/ARCHITECTURE.md).

| Stage | Deliverable | Current state |
| --- | --- | --- |
| Foundation | Repository, identity, roles, schema and API contracts | Implemented locally |
| Customer ordering | Discover → bag → checkout → receipt | Implemented locally |
| Operations | Merchant preparation → dispatch → rider delivery | Implemented locally |
| Reporting and support | Order-based metrics, exports, support and audit trail | Implemented locally |
| Mobile packaging | Shared API, native screens, app icons and build profiles | Source provided; device/store release remains |
| Controlled pilot | Real merchants, payment provider, hosted backend, monitoring | Pending |
| Public release | Signed apps, device QA, privacy materials and store review | Pending |

Do not treat local simulations as completed payment integrations. The [release checklist](docs/DEPLOYMENT.md) identifies the work needed before a commercial pilot. The local server deliberately refuses `NODE_ENV=production` until a production deployment is prepared.

## Validation

```sh
pnpm typecheck
pnpm test
pnpm build
pnpm --dir apps/mobile typecheck
pnpm --dir apps/mobile export
```

Integration tests cover order transitions and permissions, price integrity, stock, idempotency, declined payments, refunds, support, sessions and persistence. See [validation notes](docs/TESTING.md) for the checks actually performed and their limits.

## Team execution

1. Use the local demo walkthrough to agree on the order lifecycle and responsibilities.
2. Validate the five pilot zones, proposed fees and menu structure with prospective customers, merchants and riders. Record actual feedback.
3. Assign customer/mobile, merchant/rider, backend/payments, and testing/documentation owners. Avoid assigning infrastructure credentials through source control.
4. Demonstrate one complete order, one failure case and the resulting report at each milestone.
5. Finish the pilot gates in the release checklist before arranging real deliveries.

For the BIT301 hand-in, prepare the assessment's concise report and presentation using this implementation and its architecture diagram. The repository documents the system; it does not claim that field research, a rendered two-page submission or the presentation has been completed.

## Design and assets

Turquoise, deep green and warm off-white define Yebbo's identity. Food photographs load from Unsplash and require internet access. Demo menus, store names, ratings and estimates are illustrative. The original planning document retains the inspiration references. No Glovo logo, source code or branding assets are used.
