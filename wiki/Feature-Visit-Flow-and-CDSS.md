# Visit flow and CDSS

## What it is

How a health worker prioritises patients, runs a visit and gets a recommendation.

**Worklist.** The dashboard orders patients by a band plus modifier: the worst single clinical finding sets the
band (1 Severe, 2 Moderate, 3 Mild, 4 Routine); modifiers rank inside the band (`a` additional risk such as
comorbidity, first pregnancy, age 60 or over, 36 weeks or more; `b` overdue). Sort order is
`1a, 1b, 1, 2a, 2b, 2, 3a, 3b, 3, 4`, pregnant patients first within a band. Band and modifier are never shown to the health worker.

**Visit flow.** Three steps of progressive disclosure:

| Step | Screen | AI component |
|---|---|---|
| 1 | Symptom check | AI Scribe fills symptom cards; briefing cards shown |
| 2 | Vitals and the programme assessment form | AI Scribe fills fields in sequence |
| 3 | Recommendation | CDSS finding cards, counselling accordion, message draft |

Symptoms activate the relevant programme pathways (ANC, PNC, NCD, TB, IMCI, EPI, nutrition, family planning, eye care).

**CDSS.** A pure-Dart engine on the device combines FINDRISC, Framingham, trend detectors (CUSUM, EWMA, slope) over
BP history, and miniPIERS for pregnancy, plus clinical threshold rules (for example any danger sign puts a patient in band 1).

## Who uses it

Health workers; clinical leads who define thresholds.

## Repos

- [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile): `lib/core/cdss/`, `lib/features/visit/`, `lib/features/worklist/`
- AI inputs come from [leapfrog-ai-service](https://github.com/Medtronic-LABS/leapfrog-ai-service)

## Mockups

[Mockups folder](https://github.com/Medtronic-LABS/leapwell/tree/main/mockups) (`mockups/visit-flow-and-cdss/` when added).

## Open questions

Clinical thresholds and wording changes are decided by humans; raise them as
[Discussions](https://github.com/Medtronic-LABS/leapwell/discussions). Device Bluetooth integration (BP monitor, scale) is out of scope for version 1.
