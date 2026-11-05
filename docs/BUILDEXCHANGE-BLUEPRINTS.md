# Blueprint inspection and attribution record

Inspected locally on 5 November 2026. The user-specified /mnt/data paths were absent; matching named archives were available in C:/Users/chilu/Downloads. ZIP contents were read as data. No archive install, build, boot, hook or database script was executed. No supplied binaries were run. No blueprint source code, assets, credentials, databases or dependencies are incorporated into the new Django application. Workflows were independently implemented after reviewing the sources. The legacy Yebbo files are retained as user-provided project source, not attributed to these third-party projects.

## fleetbase-main.zip

- SHA-256: `9ae2caf14488275ea9f4e82851e85d2b35514a8bbd91ef275af8e5138aaa60dd`
- Entries: 1200; uncompressed bytes: 17703534; unsafe path indicators: 0.
- Stack: Laravel 10/PHP API, Ember console, SocketCluster service.
- Licence evidence: AGPL-3.0-or-later in api/composer.json; root LICENSE.md is AGPL v3.
- Review and reuse decision: Reviewed modular logistics separation, actor/time records, realtime subscription boundaries and chat receipt model. Many operational modules are external @fleetbase / composer packages, not complete local implementations in this archive. No AGPL source was copied or translated into the application.
- Dependency lockfiles present: 3. No dependency installation was performed.
- Static heuristic matches: 10. These are review indicators, not confirmed vulnerability counts; translations, tests and bundled libraries cause false positives.

Representative source paths reviewed:
- `fleetbase-main/console/app/models/chat-receipt.js`
- `fleetbase-main/console/tests/unit/models/chat-receipt-test.js`

## Construction-Management-System-master.zip

- SHA-256: `9870ac9d2e04fc10ad2dbc7cb079014d9e4d375c1db609538694836d69516674`
- Entries: 1297; uncompressed bytes: 160763359; unsafe path indicators: 0.
- Stack: ASP.NET Core MVC/C#, Razor, Entity Framework / SQL Server.
- Licence evidence: MIT, copyright 2025 Srikhar Dogiparthy.
- Review and reuse decision: Reviewed WorkOrdersController.cs, Models/WorkOrder.cs and site-worker/work-order view models. The project provides site/worker/work-order administration rather than a ready-made marketplace or item-level proof-of-receipt system. Account provisioning code contains fixed initial-password assignments requiring review if reused; none were reused. Archive contains hundreds of compiled DLLs, caches and build output, all excluded.
- Dependency lockfiles present: 0. No dependency installation was performed.
- Static heuristic matches: 10. These are review indicators, not confirmed vulnerability counts; translations, tests and bundled libraries cause false positives.

Representative source paths reviewed:
- `Construction-Management-System-master/Construction Management System/Controllers/WorkOrdersController.cs`
- `Construction-Management-System-master/Construction Management System/Models/WorkOrder.cs`
- `Construction-Management-System-master/Construction Management System/ViewModels/SiteWorker_AddWorkOrder_ViewModel.cs`
- `Construction-Management-System-master/Construction Management System/ViewModels/WorkOrder_AddSiteWorker_ViewModel.cs`

## food-delivery-multivendor-main.zip

- SHA-256: `055ead948996cecb7f01320bce0fcc420395af3dac77437d9b61c31da76a4f08`
- Entries: 6476; uncompressed bytes: 215958721; unsafe path indicators: 0.
- Stack: Next.js/React web/admin, React Native/Expo mobile, Apollo/GraphQL; backend referenced in README.
- Licence evidence: Root MIT, copyright 2023 Ninjas Code; nested web/admin MIT notices copyright 2019 Creative Tim.
- Review and reuse decision: Reviewed the multi-vendor/customer/store/rider split, order/tracking UI paths and package manifests. The shipped modules use mixed Next/React/Expo versions and remote API/key configuration. Reimplemented supplier/purchaser/transporter separation and order threads without copying payment, analytics, mobile or tracking code.
- Dependency lockfiles present: 7. No dependency installation was performed.
- Static heuristic matches: 37. These are review indicators, not confirmed vulnerability counts; translations, tests and bundled libraries cause false positives.

Representative source paths reviewed:
- `food-delivery-multivendor-main/enatega-multivendor-admin/app/(localized)/(protected)/(other-users)/admin/page.tsx`
- `food-delivery-multivendor-main/enatega-multivendor-admin/app/(localized)/(protected)/(other-users)/admin/store/coupons/page.tsx`
- `food-delivery-multivendor-main/enatega-multivendor-admin/app/(localized)/(protected)/(other-users)/admin/store/dashboard/page.tsx`
- `food-delivery-multivendor-main/enatega-multivendor-admin/app/(localized)/(protected)/(other-users)/admin/store/general/location/layout.tsx`

## Security findings and limits

The ZIP path scan found no absolute/traversal path names. Files were not extracted into the application. Compressed sizes/structures and selected text manifests were inspected; this is not a full malware analysis. The .NET archive contains binaries and development/build artifacts; copying those would add unnecessary trust risk. Fleetbase dependency manifests include broad/older version ranges (for example axios ^0.21 and Laravel 10), external package registries and install/build hooks. Multivendor modules contain provider, analytics and API configuration paths and multiple frontend dependency generations. These require independent updates, credential review and a full locked dependency audit before running their original applications. Static indicators in tests/translations do not establish exploitability.

Only the new Django runtime dependency set was queried against the public PyPI vulnerability service using pip-audit. The initial DRF 3.16.1 selection reported five known advisories; it was replaced by 3.18.3 and the final check reported no known vulnerabilities for the pinned runtime set, including psycopg-binary. This is a point-in-time dependency result, not proof of application security. The inherited Yebbo npm dependencies and all blueprint transitive dependency trees were not audited or executed.

MIT notices are preserved under blueprint-licences/ as inspection references. Since no third-party blueprint code/assets were copied, they do not purport to license the new application or the pre-existing Yebbo source. Fleetbase was used only to understand general workflow concepts; its source is not distributed. No new project-wide licence is imposed on the user repository. Obtain owner/team agreement before choosing a project distribution licence.

Framework compatibility references consulted: [Django supported releases](https://www.djangoproject.com/download/), [DRF release notes](https://www.django-rest-framework.org/community/release-notes/). Business documentation deliberately contains no external market-size or competitor capability claims requiring unsupported statistics.
