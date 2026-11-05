# API reference

Session-authenticated, same-origin JSON API. Sign in through `/login/`; `GET /` sets the CSRF cookie. Send `X-CSRFToken` on every POST. All actions reject unverified accounts. IDs are integers, quantities are whole units, money is integer ngwee (100 ngwee = ZMW 1), date-times accept ISO 8601 and use Africa/Lusaka for naive values. Prefer explicit offsets.

`GET /api/state/` returns the authorized role workspace. `POST /api/action/<action>/` applies one checked operation. No generic model update or delete route is exposed. Receipt requests may use multipart with JSON-encoded `lines` and `photos` files.

| Action | Essential fields |
| --- | --- |
| cart | listing, quantity (0 removes) |
| checkout | key (10–80 characters), site, supervisor; consumes stored multi-vendor cart |
| quote-request | listing, quantity, notes |
| quote | id, operation=reply, price_ngwee, notes; or operation=accept, site, supervisor |
| supplier-order | id, operation=ACCEPTED / READY / REJECTED; rejection requires notes |
| accept-job | id (delivery ID) |
| delivery | id, state=PICKED_UP / IN_TRANSIT / ARRIVED / CHECKPOINT, notes, source=status-only / demo / consented-gps; coordinates require latitude, longitude, consent=true |
| receipt | id (order), attest=true, notes, lines=[{line,received,condition,notes}], optional photos |
| rental-availability | listing, starts_at, ends_at |
| rental-book | listing, quantity, starts_at, ends_at |
| rental | id, operation=deposit / collect / return / cancel / refund; deposit/refund require reference, return requires notes |
| payment | id (order), operation=record / refund, reference |
| message | id (order), text |
| listing | optional id for own existing listing; name, kind=sale/rental when creating, unit, price_ngwee, stock, deposit_ngwee |
| account | username, password (12+ characters), role (non-admin) |
| verify | id (user), verified=true/false |

`GET /receipt/<order-id>/` is a printable authorized HTML document. `GET /evidence/<photo-id>/` serves authorized, re-encoded JPEG evidence with private/no-store caching. Both require order membership or admin role.

Client forms disable submit while saving. Checkout and quote acceptance replay safely. Rental booking, messages and status actions are not general idempotent endpoints; inspect state before manually retrying an uncertain rental booking. This remains an improvement before unreliable-network production use.
