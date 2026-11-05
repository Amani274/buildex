# Yebbo on iOS and Android

`apps/mobile` is a React Native/Expo application, not a WebView wrapper. It shares domain types and the API with the web application.

## Included mobile journeys

- Browse and search shops and dishes, view menus, save favourites.
- Persistent basket, customer sign-up/sign-in, saved address and optional coordinates.
- Validated checkout, welcome offer, cash or simulated mobile money.
- Order history, receipt, status timeline, in-app status updates while open, cancellation, review and repeat ordering.
- Rider job acceptance, pickup, external map directions, customer calling and cash-confirmed completion.
- Support requests/replies, password change, customer account closure and secure session storage.
- Merchant and administrator users can open the responsive web workspace.

## Development on a phone

1. Copy the root `.env.example` to `.env`. Set `HOST=0.0.0.0` only on a trusted local network.
2. Copy `apps/mobile/.env.example` to `apps/mobile/.env` and set `EXPO_PUBLIC_API_URL` to your computer's LAN address, for example `http://192.168.1.100:4000`.
3. Run the API from the repository root.
4. Run `pnpm --dir apps/mobile start` and open the application with a compatible Expo Go or development client. Expo's selected SDK must be supported by that client.
5. If a device prompts for local network access, allow it only for the intended local test. Check the host firewall if the connection fails.

Android emulators can use `http://10.0.2.2:4000`. An iOS simulator on the same Mac can use `http://127.0.0.1:4000`. A physical phone needs the computer's LAN IP. Keep the computer running during local testing.

## Build profiles

`eas.json` includes development, internal preview, and production profiles. Preview builds allow local HTTP on Android for a trusted-LAN demo. Production does not enable cleartext HTTP and must use a deployed HTTPS API.

From `apps/mobile`, after installing the official EAS CLI and signing into the team's Expo account:

```sh
eas build:configure
eas build --platform android --profile preview
eas build --platform ios --profile preview
```

Android preview creates an APK. iOS internal distribution requires Apple signing and registered test devices; TestFlight is another distribution route. Configure the appropriate environment values in EAS because ignored local `.env` files are not a reliable build-time configuration source.

Before a production build, confirm the bundle/package identifier belongs to the team, supply an HTTPS API URL, replace the preview-only backend, and configure developer accounts and signing. Then use the production build and submission profiles.

## What has not been published

There are no App Store or Google Play listings and no signed device binaries until the team's accounts and credentials are configured. A successful JavaScript export verifies bundling, not a physical-device installation or store review. These checks must remain distinct in the project report.

No background GPS tracking, remote push provider, or real mobile-money integration is enabled. In-app order refreshes run while the app is active; the order history remains authoritative.

References: [Expo build setup](https://docs.expo.dev/build/setup/), [internal distribution](https://docs.expo.dev/build/internal-distribution/), [iOS submission](https://docs.expo.dev/submit/ios/).
