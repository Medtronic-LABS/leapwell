# Mockups

Design mockups for LeapWell features, kept as files in the repo so they are reviewed, versioned and linked
from tickets and Wiki pages. This repository is **public**.

## Convention

- One folder per feature: `mockups/<feature-slug>/`, lowercase kebab-case. Suggested slugs match the Wiki feature
  pages: `ai-scribe`, `visit-briefing`, `micro-coaching`, `visit-flow-and-cdss`, `teleconsult-shukhee`,
  `household-and-enrolment`, `sync-and-offline`.
- Every folder has a `README.md` (copy [`_template/README.md`](_template/README.md)) that links the leapwell
  issue the mockup belongs to, says what it shows, which screens or flows, its status, and open questions.
- Allowed formats: HTML, PNG, SVG, PDF. Keep files small; name them by screen or step
  (`01-symptom-check.png`), not by date or author.
- A mockup is a proposal. The agreed behaviour is the acceptance criteria on the leapwell issue.

## Fake data only

No patient or member data, real names, phone numbers, IDs, addresses, credentials, tokens or environment
values, in text or in images. Use obviously fake placeholders (for example "Test Patient", `01XXXXXXXXX`).
Screenshots from a real device must come from test data only.

## CI: `mockup-scan`

The `mockup-scan` job runs `python3 scripts/sdlc/scan_text.py mockups wiki` on every PR. It scans text files
(`.md`, `.html`, `.svg`, `.txt`, `.json`, `.csv`) with the same patient-data and secret patterns the `lw-*` skills
use, prints `path:line: category` (never the matched text) and fails on any finding. It cannot read images or
PDFs, so checking those is the author's and reviewer's job. Run it locally before pushing:

```sh
python3 scripts/sdlc/scan_text.py mockups wiki
```

## How to add a mockup

1. Make sure a leapwell issue exists (or file one with `/lw-ticket`); note its number.
2. Branch `docs/<issue#>-<slug>` from `main`, copy `_template/` to `mockups/<feature-slug>/`, add the files and fill the README.
3. Run the scan above, open a PR with `Closes|Refs #<issue#>`, and get one human review.
4. After merge, link the folder from the issue and from the relevant Wiki feature page.
