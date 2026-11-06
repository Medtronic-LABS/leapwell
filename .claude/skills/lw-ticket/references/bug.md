# Bug - questions and body

Matches the GitHub form `bug.yml` in Medtronic-LABS/leapwell (template `bug`, type label `type:bug`, title prefix `[Bug] `).
Ask in this order, one at a time, skipping what is already known. Target: 10 questions or fewer.

| # | Heading (field id) | Ask | Choices / notes |
|---|---|---|---|
| 1 | Actual behaviour (`actual`) | "What went wrong? Tell me in your own words." | Usually the user's first message - confirm, don't re-ask. Capture any exact error text (scrubbed). |
| 2 | Screen or feature (`screen`) | "Which screen or part of LeapWell were you in?" | Often derivable from 1. Examples: Login, Home/worklist, Household, Visit (ANC/NCD/...), AI Scribe, Sync, Tasks, Teleconsult, Coaching dashboard. |
| 3 | Repo or component (if known) (`component`) | Only if the user seems to know: "Do you know which part of the system it is in?" | Mobile app / Frappe apps / AI Scribe / Micro-coaching / Don't know. Optional - "Don't know" or blank is fine; then the ticket gets `status:triage`. Never guess. |
| 4 | Steps to reproduce (`steps`) | "What did you tap or do, step by step, right before it happened?" | Write as a numbered list. Use roles, not people ("Open a test household"). |
| 5 | Expected behaviour (`expected`) | "What did you expect to happen instead?" | Derive if obvious ("should save") and confirm. |
| 6 | Frequency (`frequency`) | "How often does it happen?" | Always / Often / Sometimes / Once |
| 7 | Impact (`impact`) | "How much does it get in the way?" | SKs cannot work / Workaround exists / Cosmetic. Derive from 1 (crash on login = SKs cannot work; misaligned text = Cosmetic) and confirm. If a workaround exists, note it under Actual behaviour. |
| 8 | Build flavor (`build_flavor`) | "Which app or environment was it - the main LEAPWELL app (prod), LW Training, or a dev build?" | prod (LEAPWELL) / training (LW Training) / dev. For a backend or dashboard bug, ask "Which environment was it in?" and pick that. Optional: write `_No response_` if nobody knows. |
| 9 | App version (`app_version`) | "Which app version? It's in Settings > About, like 1.1.0+15." | Mobile app (or component unknown) only - skip for Frappe apps, AI Scribe and Micro-coaching and write `_No response_`. In Claude Code, offer to read it with adb (see SKILL.md). |
| 10 | Device and Android version (`device`) | "Which phone model and Android version?" | Mobile app (or component unknown) only, e.g. "Samsung Galaxy A14, Android 13"; adb can read both. Dashboard bug: the browser name. Otherwise skip and write `_No response_`. |
| 11 | Logs or screenshots (`logs`) | Only if the user mentions logs/screens: "Any error message or log lines to include?" | Optional. Scrubbed excerpt only, at most ~30 lines. Screenshots are added on GitHub after creation. |

Label mapping for a known component: Mobile app -> `area:mobile`; AI Scribe -> `area:ai`; Frappe apps -> `area:core`, or `area:shukhee` for teleconsult; Micro-coaching -> `area:coaching` (backend), `area:coaching-android` or `area:coaching-dashboard` - ask which only if unclear, otherwise `status:triage`.

## Suggested priority (never applied as a label)
- **P0** - Impact "SKs cannot work" on prod, Always/Often (e.g. cannot log in, cannot sync, data loss).
- **P1** - "SKs cannot work" on training/dev, or Sometimes/Once on prod; wrong clinical result or alert.
- **P2** - Workaround exists.
- **P3** - Cosmetic.

## Body template (headings exact; omit `### Repo or component (if known)` and `### Logs or screenshots` if empty)

```markdown
### Repo or component (if known)

Mobile app

### App version

1.1.0+15

### Build flavor

training (LW Training)

### Device and Android version

<model>, Android <n>

### Screen or feature

<screen>

### Steps to reproduce

1. ...
2. ...
3. ...

### Expected behaviour

...

### Actual behaviour

...

### Frequency

Sometimes

### Impact

Workaround exists

### Logs or screenshots

<scrubbed excerpt, or omit this section>

### Suggested priority

P2 (suggestion only - set at triage): workaround exists.

### Privacy check

- [x] This issue contains no patient/member data, names, phone numbers, IDs, credentials, tokens or unscrubbed logs (this repo is public)
```

Dropdown values must be copied exactly: Repo or component `Mobile app`, `Frappe apps`, `AI Scribe`, `Micro-coaching`, `Don't know`; Build flavor `prod (LEAPWELL)`, `training (LW Training)`, `dev`; Frequency `Always`, `Often`, `Sometimes`, `Once`; Impact `SKs cannot work`, `Workaround exists`, `Cosmetic`.
