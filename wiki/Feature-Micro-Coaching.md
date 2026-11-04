# Micro-coaching

## What it is

AI-assisted health coaching for community health workers. A backend ingests knowledge (documents, video) and
publishes learning modules; an Android SDK embeds coaching (chat, module surfaces, on-device guidance) inside the
clinical app with offline-first storage; an admin dashboard manages modules and reads analytics.

## Who uses it

- **Health workers** receive coaching inside the clinical app (Bangla by default).
- **Coaching admins** with coaching-suite access create, review and publish modules and manage the knowledge library.

## How the pieces fit

- `platform-api` serves the public API and owns PostgreSQL and analytics writes; a worker runs ingestion and
  scheduled jobs; a private `ai-runtime` does model calls. Devices never call `ai-runtime`.
- The Android SDK is a library (`.aar`) with an optional offline Bengali speech-to-text sidecar and a sample app. Hosts
  initialise it, pass the auth token after login and identify the health worker. Telemetry is OpenTelemetry-based and
  vendor-neutral.
- The dashboard (React, TypeScript) covers modules, knowledge library, ingestion and admin configuration, in English and Bangla.
- Original solution documents (platform overview, Android SDK, analytics dashboard, deployment guide, schema)
  are kept in the team's internal documents folder; ask a maintainer.

## Repos

- [spice-coaching](https://github.com/Medtronic-LABS/spice-coaching)
- [spice-coaching-android](https://github.com/Medtronic-LABS/spice-coaching-android)
- [spice-coaching-dashboard-ui](https://github.com/Medtronic-LABS/spice-coaching-dashboard-ui)

Integration branch for all three is `leapwell-main`.

## Mockups

[Mockups folder](https://github.com/Medtronic-LABS/leapwell/tree/main/mockups) (`mockups/micro-coaching/` when added).

## Open questions

Raise as [Discussions](https://github.com/Medtronic-LABS/leapwell/discussions). To decide: how coaching surfaces in
the Apon Sushashthya app versus the SPICE clinical app it was first built for.
