---
name: lw-release
description: Walk a LeapWell release checklist for one repo - version bump PR, readiness check, release notes, and (mobile) the signed build check. Prepares notes and the checklist only; never tags, uploads, deploys or publishes unless the human runs it.
argument-hint: "<repo-key> [version]"
disable-model-invocation: true
---

# Release $ARGUMENTS

The human releases; you prepare and check. `$ARGUMENTS` is `<repo-key> [version]`; read the repo's `repos.json` entry (`name`, `integration_branch`, `verify`, `notes`). Process reference: `docs/process/SDLC.md`.

1. **Version.** Find the repo's single version source (mobile `pubspec.yaml`; Python `pyproject.toml` or the package `__version__`; dashboard `package.json`; Android Gradle `versionName` / `versionCode`) and the last tag (`git -C repos/<name> tag --list --sort=-v:refname`). Agree the next version with the user (build numbers always increase).
   If a bump is needed: create `chore/<N>-bump-<version>` (N = the release sub-issue in this repo) with `git -C repos/<name> switch -c <branch> origin/<integration_branch>`, change only the version, commit `chore(release): bump version to <version> (#<N>)`, and open a draft PR with `/lw-pr`. Never bump on the integration branch or `main` directly.

2. **Release issue.** Make sure a `[Release] <key> <version>` issue exists in leapwell (file it with `/lw-ticket` if not - it previews and files only on an explicit yes).

3. **Readiness.** Dispatch the `lw-release` agent with the repo key for the checklist (CI on the integration branch, open P0/P1 bugs, verification). Show its report.

4. **Release notes.** Draft from merged PRs / closed issues since the last tag (`gh pr list -R Medtronic-LABS/<name> --base <integration_branch> --state merged --search "merged:>=<last-tag-date>"`): user-facing language, no internal IDs or patient data. Mobile: **English and Bangla**, each **500 characters or fewer** - count and show the counts. The user approves the wording.

5. **Build.**
   - **Mobile** - the human runs these on a machine with the release key, one per app, inside `repos/uhis_lf_mobile`:
     - LEAPWELL (prod): `scripts/release.sh production ""`
     - LW Training: `scripts/release.sh training "" --app-flavor training`
     The empty `""` keeps the current pubspec version (already bumped). The script refuses debug signing and runs the signer check. You may explain its output; you never handle the key, `key.properties` or `env*.json`.
   - **Other repos** - show the repo's `verify.build` (skip if empty, show `notes`) and point to its own image / deploy pipeline. Prepare the notes and checklist only; tags, GitHub releases and deploys are human-only.

6. **Tag and publish - human only.** Only if the human explicitly says "tag it" in this session, show the exact command (mobile: `scripts/release.sh production "" --tag`, then `git push origin v<version>`; other repos: `git -C repos/<name> tag -a v<version> -m "<notes title>"` and `git -C repos/<name> push origin v<version>`) and let the human run it. Play Console upload and production deploys are done by the human.

7. **After release.** Remind: tick the release issue, back-merge `main` into the integration branch if a hotfix went out.

Never tag, push tags, upload, deploy, publish a GitHub release or merge on your own; never set priority.
