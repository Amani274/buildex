# BuildExchange ZM — operational prototype update

This update turns the local demo into a buyer-facing construction marketplace, separate equipment-rental workflow, delivery workspace, site-receiving desk and customer-support desk. The working name remains BuildExchange ZM. Use **Start BuildExchange.cmd** from the project root; it applies additive migrations and seeds the six research storefronts without resetting orders or existing stock.

## Demonstrate the full workflow

1. Sign in as **buyer**. Discover contains six researched sample storefronts and 37 product samples. Select a supplier, search or choose a category. Product illustrations are original; prices say either Demo price or Published snapshot. The real catalogue and hours source are linked in storefront information.
2. Add materials to the basket. Click the map to choose a fictional site and enter a landmark. Review materials, delivery estimate, loading/unloading labour and the 5% demo platform fee before placing the order. The server recomputes fees and splits orders by supplier.
3. Continue to a **demo bank** (Absa, Zanaco, FNB or Stanbic are labels only). The gateway displays a fictitious ZMW 100,000 balance for each demo bank account. Approve, decline or cancel without entering any bank credentials. Approval debits only that local simulated balance and creates a receipt. A retry cannot debit the same transaction twice; a declined transaction leaves the order unpaid and can be retried.
4. Sign in as the relevant **supplier** account: chilanga, builders, micmar, lamasat, handymans or camco. A supplier can accept a paid order, mark it ready or decline it with a reason. A paid declined order has a separate simulated refund that credits its original demo account once.
5. Sign in as **driver**. Accept the ready job, then open its controls, confirm collection and start delivery. Consent to location sharing and choose **Rehearse demo movement**. The vehicle marker moves and the trace is stored as source=demo. GPS is a separate explicit action; no automatic permission request or fake live GPS is used. The recipient sees refreshed positions approximately every five seconds while the tracking screen is open. The dashed connection and rehearsal trace are not road-routing instructions.
6. Record arrival separately. Sign in as **supervisor**, inspect quantities/condition and confirm the site receipt. A shortage/damage becomes a discrepancy; full good receipt becomes received. Private photos are optional. Customer views contain concise operational information; raw audit details and image hashes stay out of customer payloads and receipts.
7. A participant can use **Get help** to open an order case. Sign in as **admin** (now customer support): only submitted cases and their relevant order details appear. Support can respond and update case status, but cannot shop, dispatch, change prices, provision accounts or record payments/refunds. The account is no longer a Django superuser or staff user.

## General equipment rentals

Choose Rent equipment in Discover. These are independent simulated hire listings, not a claim that the six named suppliers provide rentals. Check the date range, book, then pay the rental charge plus refundable deposit through the demo bank gateway. The equipment owner records collection during the booked period and inspects the return. Returning credits only the deposit to the fictitious bank balance, retaining the rental charge; cancelling an uncollected paid booking refunds the entire simulated amount. Capacity, adjacent bookings and overdue equipment checks remain enforced.

Legacy equipment owners are supplier (drill) and supplier2 (generator/pump). All demo account passwords remain **BuildDemo2026!**, unless DEMO_PASSWORD was set when they were first created. No existing user password is overwritten by seeding.

## Phone GPS and map boundaries

The map uses locally bundled MapLibre GL JS and the OpenFreeMap public vector service with OpenMapTiles/OpenStreetMap attribution. Standard OSM raster tiles were blocked in browser verification and are no longer requested by the application. Map style/font/vector requests need internet access and WebGL. No API key is required by the selected public service. First map loading can be slower than subsequent cached views. There is no offline map pack.

The GPS action uses navigator.geolocation.watchPosition. It shares coordinates only for the assigned active job, after in-app consent and browser permission. It stops when you leave the tracking screen, hide the tab, stop sharing, sign out or close the page. A phone cannot reach this PC through its own 127.0.0.1 address. Physical-phone use requires an explicitly configured, reachable HTTPS address and browser permission; ordinary insecure LAN HTTP does not meet browser geolocation requirements. Device GPS has not been verified on a physical phone. Do not change browser security settings to work around this. Use the clearly labelled movement rehearsal for the local classroom demonstration.

The site pins and supplier pins are approximate demonstration coordinates, not verified pickup gates. Distance = great-circle distance × 1.35. ETA starts after dispatch and includes a simple preparation/weight allowance, with no live traffic or routing provider. Published/directory hours are informational; suppliers manually accept the demo jobs even if their real showroom is closed. Do not treat a demo acceptance as a real-store dispatch promise.

## Demonstration fee rules

Money is stored as integer ngwee. The simulated platform fee is 5% of materials, rounded to the nearest ngwee. Delivery uses a weight-based base rate (K35 for ≤20 kg, K65 for ≤1,000 kg, otherwise K140) plus K6.50 per estimated kilometre. Loads over 5,000 kg are modelled as additional trips. Loading/unloading labour is zero for ≤20 kg, otherwise K25 plus K15 per started 250 kg. Product weights are demo assumptions; these are not actual merchant, transporter or worker rates.

## Local checks

From buildexchange/ run the Python interpreter in your virtual environment with `manage.py test exchange`, `manage.py check` and `manage.py makemigrations --check --dry-run`. Use **seed_demo** then **seed_marketplace** after migrations for a fresh database. The Windows launcher runs both seeds automatically. Original order records remain intact; the older generic sale listings are hidden from the buyer discovery page while their historic orders remain readable.
