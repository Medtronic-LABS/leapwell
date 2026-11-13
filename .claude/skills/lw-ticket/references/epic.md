# Epic - questions and body

Matches the GitHub form `epic.yml` in Medtronic-LABS/leapwell (template `epic`, type label `type:epic`, title prefix `[Epic] `).
An epic is a large goal that groups several feature requests and spans sprints. If the user describes one
concrete capability, file a **Feature** instead. Ask one at a time, skipping what is known.

| # | Heading (field id) | Ask | Notes |
|---|---|---|---|
| 1 | Goal (`goal`) | "What outcome should this epic deliver, and for whom?" | One or two sentences; the outcome, not a list of screens. |
| 2 | Scope (`scope`) | "What is in, and what is deliberately left out?" | Draft an in / out list from what was said and confirm. |
| 3 | Success measures (`success`) | "How will we know the epic is done?" | Observable results, not tasks. |
| 4 | Target release or date (`target`) | Only if mentioned. | Optional. The team sets dates on the roadmap. |

Features are added to the epic afterwards as its sub-issues (on GitHub: "Create sub-issue" or "Add existing issue").

## Suggested priority (never applied as a label)
- **P1** - tied to a pilot or rollout commitment.
- **P2** - planned for the coming quarter.
- **P3** - longer-term direction.

## Body template (headings exact; omit `### Target release or date` if empty)

```markdown
### Goal

...

### Scope

In: ...
Out: ...

### Success measures

...

### Target release or date

<release or date, or omit this section>

### Suggested priority

P2 (suggestion only - set at triage): ...

### Privacy check

- [x] This issue contains no patient/member data, names, phone numbers, IDs, credentials, tokens or unscrubbed logs (this repo is public)
```
