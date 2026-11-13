# Filing a LeapWell ticket

For QA, PM and anyone else reporting a problem or asking for something in LeapWell (the Apon Sushashthya
app, the Frappe backend, AI Scribe, teleconsult, micro-coaching). **File everything in the leapwell
repository.** You never need to know which code repo is affected; a developer routes it.

## Idea or ticket?

- **Early idea, field feedback, partner request, question:** start a **Discussion**
  (<https://github.com/Medtronic-LABS/leapwell/discussions>). When the team agrees, the PM promotes it to a ticket.
- **Anything concrete (bug, feature request, task, release):** file a ticket as below.

## Two ways to file

- **Claude chat (web or Desktop):** just say *"file a bug"* (or "I want to request a feature"). The
  `lw-ticket` skill takes over and interviews you.
- **Claude Code:** type `/lw-ticket`.

Claude asks one question at a time, checks whether the problem is already reported, shows you the full
ticket, and creates it **only after you say yes**. You get the link back.

## What Claude will ask

- **Bug:** app version, build (prod / training / dev), phone and Android version, which screen, the steps,
  what you expected, what happened, how often, how badly it blocks work. The repo or component is optional.
- **Feature:** who needs it, the problem today, the idea, how we will know it works, which programme
  (ANC, NCD, ...), and what should happen offline.
- **Task:** what, why now, and the risk if we don't do it.

If you don't know something (for example the app version), say so; Claude helps you find it or marks it
unknown. It suggests a priority, but the team sets the real priority at triage.

## Privacy rule: this repository is public

Anyone on the internet can read every ticket, Discussion, Wiki page and mockup. Never include patient or
member names, phone numbers, IDs, addresses, passwords, tokens, environment values or raw logs. Claude
replaces these with placeholders and tells you what it removed. A security problem (a login bypass, one user
seeing another's data) is **not** filed as a ticket: report it privately at
<https://github.com/Medtronic-LABS/leapwell/security/advisories/new> and tell the team lead.

## Screenshots

Claude cannot attach images. After the ticket is created, open the link and drag your screenshot into a
comment. Only screenshots from **test data**, never a real patient.

## No Claude? Use the web forms

Open <https://github.com/Medtronic-LABS/leapwell/issues/new/choose>, pick Bug report, Feature request,
Task or Release, fill every required field and tick the privacy box.

## What happens next

1. The ticket is added to the LeapWell board in **Triage**. If something is missing, a bot adds
   `status:needs-info` and comments what to add; edit the ticket and the label goes away.
2. The team triages **twice a week**: sets priority, size and owner, and moves it on
   (Triage → Backlog → Ready → ... → Done).
3. A developer routes it (`/lw-route`) into one sub-issue per affected repo. The ticket gets
   `status:routed` and you can follow progress through its sub-issues.
4. When every sub-issue is closed, the ticket closes itself within the hour with a comment listing them.

## Labels

| Label | Meaning |
|---|---|
| `type:bug` / `type:feature` / `type:task` / `type:release` | Bug, feature request, internal task, release tracking |
| `area:*` | Repo or part of the product (e.g. `area:mobile`, `area:sync`, `area:ai`) |
| `env:prod` / `env:training` / `env:dev` | Which build the bug was seen in |
| `prio:P0` | Drop everything: health workers cannot work |
| `prio:P1` | Fix this sprint |
| `prio:P2` / `prio:P3` | Planned / nice to have |
| `status:needs-info` | Waiting for the reporter to complete the ticket |
| `status:triage` | Repo or component unknown; a developer routes it |
| `status:routed` | Sub-issues created; closes when they all close |
| `status:blocked` / `status:needs-design` | Waiting on something else / on a design decision |
