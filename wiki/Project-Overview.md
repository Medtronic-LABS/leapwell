# Project overview

## What LeapWell is

LeapWell (the Leap Well Project) is the next-generation frontline experience of the UHIS programme. Its main
product is **Apon Sushashthya**, a Flutter, Android-first mobile app that turns form filling and data collection
into AI-assisted care delivery. It sits on a Frappe server of record, AI services for scribing and briefing, and
a micro-coaching platform.

## Who uses it

- **Health workers (SKs / CHWs)** visit households, assess patients (ANC, PNC, NCD, TB, IMCI and more), refer, and follow up.
- **Clinicians** receive referrals and teleconsults.
- **Programme managers and coaches** manage coaching modules and read analytics.
- **PM, QA and developers** work in the [leapwell repository](https://github.com/Medtronic-LABS/leapwell).

## Principles

- **Offline-first.** Data is stored on the device in an encrypted database and synced opportunistically.
- **AI proposes, a human decides.** Every AI output is a proposal until the health worker accepts it, and carries a rationale.
- **Household-centred.** Care is organised around households and their members.
- **Explainable.** Recommendations show why. Risk bands drive worklist order and are not shown to the health worker.
- **Privacy.** Session tokens only on the device; no patient data in tickets, docs or this Wiki.

## How the pieces fit

1. The mobile app talks to the backend over HTTP, with an offline queue and a local encrypted database.
2. The Frappe apps hold clinical data and expose the sync API; a second app integrates the Shukhee calling system.
3. The AI service turns audio into clinical fields and generates visit briefing cards.
4. The micro-coaching platform has a backend, an Android SDK that embeds in the clinical app, and an admin dashboard.

See [Repos and areas](Repos-and-Areas) for which repo owns what, and the feature pages for detail.

## Open questions

Raise them as [Discussions](https://github.com/Medtronic-LABS/leapwell/discussions).
