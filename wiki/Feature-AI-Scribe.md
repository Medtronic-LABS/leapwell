# AI Scribe

## What it is

Voice-to-form for the visit. The health worker records the consultation; the AI service transcribes it and
extracts structured clinical fields (diagnosis, blood pressure, blood glucose, comorbidities, complications,
clinical notes, chief complaints). The app shows the draft as a banner that fills the assessment form fields
in sequence. The health worker reviews and **accepts or rejects**; acceptance is the moment it becomes part of the record.

## Who uses it

Health workers during Step 1 (symptom check) and Step 2 (vitals and assessment forms: ANC, NCD, TB, IMCI, PNC).

## How it works

1. The app checks mic permission and records. Audio of 1 MB or more is uploaded in chunks (resumable, for low
   bandwidth); smaller audio is posted directly.
2. The app polls the job until it completes, then maps the SOAP-style result into form field values.
3. Every output carries a rationale: model version, confidence, ASR provider, LLM model, source segments and a
   human-review flag. The accept action logs the rationale snapshot.
4. A beta **LIVE** toggle in the same banner streams a real-time transcript and an on-demand symptom preview. It is a
   listening aid only and feeds nothing into the saved note. It is native-only (not available on web).

## Repos

- [leapfrog-ai-service](https://github.com/Medtronic-LABS/leapfrog-ai-service): scribe, upload and prompt files (private repo)
- [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile): `lib/features/scribe/` and the realtime ASR controller

## Mockups

[Mockups folder](https://github.com/Medtronic-LABS/leapwell/tree/main/mockups) (`mockups/ai-scribe/` when added; see the mockups README).

## Open questions

Raise as [Discussions](https://github.com/Medtronic-LABS/leapwell/discussions). Known gap: a hung LLM call has no
timeout and can silently drop the rest of a realtime session's extractions (tracked in the AI service repo).
