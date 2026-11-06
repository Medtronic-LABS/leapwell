# Teleconsult (Shukhee)

## What it is

Teleconsultation support through the external **Shukhee** calling/telephony system. The integration is a Frappe app
that maps credentials between UHIS users and Shukhee, holds its settings, and keeps an audit log of calls. The
mobile app has a teleconsult screen (`/teleconsult`) as its entry point.

## Who uses it

- **Health workers** reach teleconsult from the app.
- **Clinicians** take part in the call.
- **Administrators** configure the integration settings and review the call audit log.

## How it works

The `shukhee_integration` app sits on the Frappe backend and talks to Shukhee. Credentials are mapped and
configured in the app's settings on the server, never in source or in this repo. Calls are recorded in an audit
log. The app targets Frappe version 16 (see the local Frappe bench in the repository's `env/frappe`). The exact
call flow is still to be written down (see open questions).

## Repos

- [leapwell_shukhee_integration](https://github.com/Medtronic-LABS/leapwell_shukhee_integration): the Frappe app
- [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile): teleconsult screen
- [frappe_spice_next_core](https://github.com/Medtronic-LABS/frappe_spice_next_core): the server of record it runs beside

## Mockups

[Mockups folder](https://github.com/Medtronic-LABS/leapwell/tree/main/mockups) (`mockups/teleconsult-shukhee/` when added).

## Open questions

Raise as [Discussions](https://github.com/Medtronic-LABS/leapwell/discussions). To define: exact call flow from the
health worker's request to the clinician, what is stored in the audit log, and consent handling for calls.
