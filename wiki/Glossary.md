# Glossary

| Term | Meaning |
|---|---|
| Apon Sushashthya | The LeapWell mobile app for health workers (Flutter, Android-first) |
| SK / CHW | Frontline community health worker, the app's main user |
| Programme | A care pathway: ANC, PNC, NCD, TB, IMCI (iCCM), EPI, nutrition, family planning, cataract, eye care |
| ANC / PNC | Antenatal / postnatal care |
| NCD | Non-communicable disease care (hypertension, diabetes) |
| TB | Tuberculosis programme |
| IMCI / iCCM | Integrated management of childhood illness / community case management |
| EPI | Expanded programme on immunisation |
| GA | Gestational age in weeks |
| BP / BG / Hb | Blood pressure / blood glucose / haemoglobin |
| GDM | Gestational diabetes mellitus |
| Band | Worklist urgency level 1 to 4 (Severe, Moderate, Mild, Routine); sets sort order only |
| Modifier | `a` additional risk, `b` overdue; ranks patients inside a band |
| Worklist | The dashboard list of patients ordered by band and modifier |
| Visit flow | Three steps: symptom check, vitals and assessment form, recommendation |
| CDSS | Clinical decision support: rule and algorithm engine that raises findings and alerts |
| AI Scribe | Voice to structured clinical fields, accepted or rejected by the health worker |
| Rationale | Payload explaining an AI output: model, confidence, sources, human review flag |
| Proposal | An AI output that is not part of the record until a human accepts it |
| Household | A first-class group of members, the unit of enrolment and visits |
| Member | A person in a household who receives care |
| Referral | A hand-off of a patient to a clinician or facility, with status |
| Shukhee | External calling/telephony system used for teleconsult |
| Micro-coaching | AI-assisted short coaching modules and chat for health workers |
| Sub-issue | A code-repo issue linked to a leapwell item; the "how" of a ticket |
| Integration branch | The branch PRs target in a repo (`develop`, `development` or `main`) |
| FHIR R4 | The healthcare data standard used at API boundaries |
| Frappe | The Python web framework the server of record is built on |

Terms are added by pull request to `wiki/Glossary.md` or by editing this page (`/lw-wiki Glossary`).
