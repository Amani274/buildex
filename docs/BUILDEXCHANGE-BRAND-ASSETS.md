# Brand and visual assets

**Primary tagline: From yard to site.**

Supporting lines used in the application: **Big plans. Better deliveries.** / **Less chasing. More building.** / **Every handoff matters.**

The original mark combines a building outline with an amber receiving check. Its rounded navy square reads clearly as an app icon; the house shape refers to the project site, while the check represents an accountable handoff. The colour system uses soft dark navy #073B5C, clear blue #087BB5, construction amber #FFB638 and pale blue-grey surfaces. It does not use Barclays, Yango or supplier logos.

The active hero and sign-in photograph is the construction photo supplied by the project owner on 5 November 2026 (`construction-photo.jpeg`). It is copied unchanged, with responsive CSS display cropping. Its photographer and public reuse licence were not supplied; it is excluded from the original artwork dedication. The previous generated illustration is retained as a historical unused asset.

Four real catalogue photographs were sourced from Wikimedia Commons. They are representative category examples rather than exact retailer product photos, and are labelled accordingly. Files are downloaded locally so their display does not depend on a third-party hotlink. The drill and grinder files remain under CC BY-SA 4.0, separately from application code. Originals are unchanged and scaled to fit in the UI. Sources were verified on 5 November 2026.

| Asset | Source / licence record |
| --- | --- |
| Logo, remaining product illustrations, vehicle marker | Original project artwork; CC0-1.0 dedication. |
| construction-photo.jpeg | User supplied; no public reuse licence asserted. |
| cement-photo.jpg | [Portland Cement Bags](https://commons.wikimedia.org/wiki/File:Portland_Cement_Bags.jpg), KVDP, public domain dedication. |
| wheelbarrow-photo.jpg | [Wheelbarrow in the field](https://commons.wikimedia.org/wiki/File:Wheelbarrow_in_the_field.jpg), Hyena, public domain dedication. |
| drill-photo.jpg | [Makita 18v electric drill](https://commons.wikimedia.org/wiki/File:Makita_18v_electric_drill.jpg), Helar Lukats, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). |
| grinder-photo.jpg | [Makita DGA504 free](https://commons.wikimedia.org/wiki/File:Makita_DGA504_free.jpg), Widar23 and Bukk, [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). |
| MapLibre GL JS 6.4.1 | Official npm distribution; BSD-3-Clause and bundled third-party notices retained in vendor/maplibre/LICENSE.txt. |
| Leaflet 1.9.4 | Downloaded during initial map work; its BSD licence is retained. The final runtime uses MapLibre instead. |
| OpenFreeMap map service | [Public service](https://openfreemap.org/) and [integration guide](https://openfreemap.org/quick_start/). Free public maps without a key; attribution retained. Service availability is external. |
| Map data and cartography | OpenMapTiles/OpenStreetMap attribution appears on the map; data rights remain with their respective open licences. No bulk tile download or map pack is distributed. |

The supplied ZIP blueprints were inspected again for their TrackingRider / useOrderTracking patterns: authorized job-location updates, a latest-location marker, lifecycle start/stop and order-state subscriptions. These ideas were independently implemented with consented browser geolocation, role-checked location updates and five-second recipient refresh. Their React Native/Apollo code and Fleetbase AGPL source were not copied into Django. Original blueprint attributions remain in BUILDEXCHANGE-BLUEPRINTS.md.

The public `/image-credits/` page provides photographer credits, source and licence links, modification statements and exact-model caveats. A credit link appears on each photographic product card and in the sidebar.
