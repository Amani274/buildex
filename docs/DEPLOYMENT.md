# Public launch checklist

This version is a fully connected **local pilot/demo**, not a live commercial delivery service. The server refuses NODE_ENV=production to prevent accidental public deployment with known demo accounts.

Before moving beyond the local pilot:

1. Choose hosting and an HTTPS API domain. Revisit the deferred Supabase/PostgreSQL decision with the owner.
2. Replace development accounts with verified sign-up, staff onboarding, account recovery, email delivery, appropriate session controls and operator-managed access.
3. Move entity records to a normalized, migrated production schema; implement retention, backup/restore monitoring and operational alerts.
4. Validate real merchants, menus, opening hours, stock and rider operations. The seeded shops and ratings are fictional.
5. Integrate a licensed payment provider only after onboarding. Verify webhook signatures, idempotency, settlement and refunds in a sandbox. Remove simulation options from real checkout.
6. Establish delivery-zone accuracy, live support staffing, rider compensation, merchant settlement and a refund policy.
7. Test iOS and Android binaries on physical devices, including slow/offline conditions, screen readers and large text.
8. Configure Expo and store ownership, signing credentials, privacy disclosures, screenshots, reviewer accounts and account deletion requirements.
9. Submit signed builds for review and add actual download links only after approval.

The included EAS profiles prepare the build path. They do not create store accounts, purchase services or approve a release.
