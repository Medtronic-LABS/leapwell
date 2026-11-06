# Repos and areas

LeapWell code lives in seven repositories under the Medtronic-LABS org. The authoritative table (integration
branches, verify commands) is [REPOS.md](https://github.com/Medtronic-LABS/leapwell/blob/main/docs/process/REPOS.md).

| Area | Repo | Stack | What it holds |
|---|---|---|---|
| Mobile app | [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile) | Flutter | Apon Sushashthya: worklist, household and visit flows, CDSS, AI Scribe client, offline database |
| Frappe apps | [frappe_spice_next_core](https://github.com/Medtronic-LABS/frappe_spice_next_core) | Frappe (Python) | Server of record: clinical data model, sync API, dynamic forms, FHIR R4 egress, risk scoring, AI narratives |
| Frappe apps | [leapwell_shukhee_integration](https://github.com/Medtronic-LABS/leapwell_shukhee_integration) | Frappe (Python) | Integration with the Shukhee calling system: credential mapping, settings, call audit log |
| AI Scribe | [leapfrog-ai-service](https://github.com/Medtronic-LABS/leapfrog-ai-service) | Python FastAPI | Scribe, chunked upload, visit briefing, programme recommendation (private repo) |
| Micro-coaching | [spice-coaching](https://github.com/Medtronic-LABS/spice-coaching) | Python | Platform API, worker, AI runtime, shared contracts |
| Micro-coaching | [spice-coaching-android](https://github.com/Medtronic-LABS/spice-coaching-android) | Kotlin | Android SDK embedded in the clinical app, optional offline speech-to-text, sample app |
| Micro-coaching | [spice-coaching-dashboard-ui](https://github.com/Medtronic-LABS/spice-coaching-dashboard-ui) | TypeScript / Vite | Admin dashboard: modules, knowledge library, ingestion, analytics |

## Features to repos

| Feature | Repos |
|---|---|
| [AI Scribe](Feature-AI-Scribe) | leapfrog-ai-service, uhis_lf_mobile |
| [AI visit briefing](Feature-Visit-Briefing) | leapfrog-ai-service, uhis_lf_mobile |
| [Micro-coaching](Feature-Micro-Coaching) | spice-coaching, spice-coaching-android, spice-coaching-dashboard-ui |
| [Visit flow and CDSS](Feature-Visit-Flow-and-CDSS) | uhis_lf_mobile |
| [Teleconsult (Shukhee)](Feature-Teleconsult-Shukhee) | leapwell_shukhee_integration, uhis_lf_mobile |
| [Household and enrolment](Feature-Household-and-Enrolment) | uhis_lf_mobile, frappe_spice_next_core |
| [Sync and offline](Feature-Sync-and-Offline) | uhis_lf_mobile, frappe_spice_next_core |

## Tickets and labels

Everything is filed in leapwell. Each repo has an `area:<key>` label (`area:mobile`, `area:core`, `area:shukhee`,
`area:ai`, `area:coaching`, `area:coaching-android`, `area:coaching-dashboard`). A developer routes a ticket
into one sub-issue per affected repo.
