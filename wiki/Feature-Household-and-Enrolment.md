# Household and enrolment

## What it is

The household is the unit of care. A household has members; members are enrolled into programmes and visited.
The app lets a health worker list and search households and members, open a household or a member's context
(history, assessments, referrals), and enrol new households and members offline.

## Who uses it

Health workers doing household visits and enrolment.

## What the app offers

- Household list and detail, member list, patient context screen with assessment history.
- A unified search bar for patients and households; it detects phone, national ID or name and debounces queries.
- Household enrolment flow: create household, success screen, add member.
- Referral list and detail for the tasks tab.

## Data

On the server the clinical data model has Patient, Household, Case (episode of care), Encounter, Observation,
Condition, Referral, Task, Programme, Care Team, Facility and a multi-level Geography hierarchy. Household is also
produced as a FHIR R4 `Group` at the API boundary. Records created offline are queued locally and uploaded when
a connection is available (see [Sync and offline](Feature-Sync-and-Offline)).

## Repos

- [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile): `lib/features/household/`, `lib/features/search/`, `lib/features/referral/`
- [frappe_spice_next_core](https://github.com/Medtronic-LABS/frappe_spice_next_core): data model and sync API

## Mockups

[Mockups folder](https://github.com/Medtronic-LABS/leapwell/tree/main/mockups) (`mockups/household-and-enrolment/` when added).

## Open questions

Raise as [Discussions](https://github.com/Medtronic-LABS/leapwell/discussions). To decide: duplicate-member handling
at enrolment and how households are scoped to a health worker's catchment.
