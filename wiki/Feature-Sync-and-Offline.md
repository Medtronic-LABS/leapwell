# Sync and offline

## What it is

The app works fully without a connection and syncs when it can. The first login does a cold sync of the health
worker's patients, households, referrals and assessments; later pulls fetch deltas. Assessments created offline are
stored in the local database and uploaded in batches, each with a sync status (pending, synced, network error).

## Who uses it

Health workers, often with poor or no connectivity.

## How it works

- **On device:** an AES-256 encrypted SQLite database (SQLCipher) with a per-device key kept in the platform key
  store. If the file is not a valid encrypted database it is recreated.
- **Session:** only session tokens are stored (secure storage); never the username, password or a hash. The app
  locks when it goes to the background, and biometric or PIN unlocks the stored session.
- **Server:** the Frappe core app provides a cursor-based `sync.push` / `sync.pull` API, idempotent on a client
  operation id and scoped server-side to the user's catchment. Forms are metadata-driven, with conditional
  navigation evaluated identically on device and server. Mobile today also uses the existing offline-sync
  endpoints of the UHIS backend; moving fully to the core sync API is a design question.
- **Conflict handling:** append-only guardrails on Encounters and Observations on the server.

## Repos

- [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile): `lib/core/db/`, `lib/features/sync/`, `lib/core/api/`
- [frappe_spice_next_core](https://github.com/Medtronic-LABS/frappe_spice_next_core): sync API and data model

## Mockups

[Mockups folder](https://github.com/Medtronic-LABS/leapwell/tree/main/mockups) (`mockups/sync-and-offline/` when added).

## Open questions

Raise as [Discussions](https://github.com/Medtronic-LABS/leapwell/discussions). To decide: the migration path to the
core sync API, retry and back-off rules, and what the health worker sees when sync fails repeatedly.
