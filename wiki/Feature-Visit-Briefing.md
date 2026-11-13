# AI visit briefing

## What it is

Three collapsible cards shown to the health worker on the symptom-picker screen before a visit. They are fetched
while the worker reviews symptoms.

| Card | Content |
|---|---|
| Before You Knock | An AI headline and 3 to 5 bullets on the patient's most important concerns |
| Today's Priorities | A numbered list of 3 to 5 specific, actionable priorities for this visit |
| Suggested Discussion Points | A culturally appropriate opening line and topic sections with 2 to 3 open-ended questions each |

The service also returns a contextual greeting in Bangla.

## Who uses it

Health workers, just before and at the start of a visit.

## How it works

The app builds a request from the local patient context, recent vitals and open follow-ups, and calls the briefing
endpoint of the AI service, which reads recent clinical history and generates the cards with an LLM. If the service
is unavailable the app degrades gracefully: card 1 falls back to local rule-based context chips and cards 2 and 3
show an "AI unavailable" message. The briefing never blocks the visit.

## Repos

- [leapfrog-ai-service](https://github.com/Medtronic-LABS/leapfrog-ai-service): briefing service and its prompt files (private repo)
- [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile): `lib/features/visit/briefing/`

## Mockups

[Mockups folder](https://github.com/Medtronic-LABS/leapwell/tree/main/mockups) (`mockups/visit-briefing/` when added).

## Open questions

Raise as [Discussions](https://github.com/Medtronic-LABS/leapwell/discussions).
