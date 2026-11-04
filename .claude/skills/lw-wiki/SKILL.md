---
name: lw-wiki
description: Edit a page of the LeapWell GitHub Wiki (project overview, repos and areas, feature pages, glossary) - clone the wiki to a temp dir, make the edit, privacy-scan, show the diff, and push only after an explicit yes.
argument-hint: <page-name, e.g. Feature-AI-Scribe>
disable-model-invocation: true
---

# Edit wiki page $ARGUMENTS

The GitHub Wiki of `Medtronic-LABS/leapwell` is the live copy of the project and feature pages (seeded from `wiki/` by `scripts/github/publish_wiki.sh`). Process docs (SDLC, tickets, requirements, admin setup) are **not** wiki pages: they live in `docs/process/` and change by PR - if the user wants to change process, say so and stop.
The wiki is public: no patient data, real names, partner-confidential details, tokens or env values. Mockup links point to `mockups/<feature>/` in the repo.

1. **Clone** to a fresh temp dir:
   ```
   mktemp -d
   git clone https://github.com/Medtronic-LABS/leapwell.wiki.git <tmpdir>/wiki
   ```
   If the clone fails with "repository not found", the wiki has no first page yet - tell the user to run `scripts/github/publish_wiki.sh` (it prints the one UI step) and stop.

2. **Find the page.** Page files are `<Page-Name>.md` (spaces become hyphens). If `$ARGUMENTS` is empty or does not exist, list the `*.md` files and ask which one (or whether to create a new page, and which page links to it).

3. **Edit.** Ask what to change, then edit with the Edit tool. Keep pages short and factual; link repos as `https://github.com/Medtronic-LABS/<name>` and tickets as `Medtronic-LABS/leapwell#N`; repo facts must match `repos.json`.

4. **Privacy scan.** `python3 scripts/sdlc/scan_text.py <tmpdir>/wiki` must report nothing; it prints categories only. Fix any finding and re-run. Also read the diff yourself for names, phone numbers, IDs and partner details the scanner cannot catch.

5. **Show the diff.** `git -C <tmpdir>/wiki diff` (and `git -C <tmpdir>/wiki status --short` for new pages). Ask: "Push this change to the wiki? (yes / change something)". Push only on an explicit yes.

6. **Commit and push** (after yes):
   ```
   git -C <tmpdir>/wiki add <files>
   git -C <tmpdir>/wiki commit -m "docs(wiki): <what changed>"
   git -C <tmpdir>/wiki push origin HEAD
   ```
   If the push is rejected (someone else edited), `git -C <tmpdir>/wiki pull --rebase`, show the new diff and ask again.

7. **Clean up** the temp dir and report the page URL `https://github.com/Medtronic-LABS/leapwell/wiki/<Page-Name>`.

Never push without an explicit yes; never force-push; never delete a page unless the user asked for that page by name.
