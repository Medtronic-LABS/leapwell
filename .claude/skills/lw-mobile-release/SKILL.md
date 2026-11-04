---
name: lw-mobile-release
description: Build a release artifact of the LeapWell Flutter app (repos/uhis_lf_mobile) for dev, training or playstore - verifies signing and freshness, copies the artifact to releases/. Builds only; merging, tagging and the Play upload stay with a human.
argument-hint: <dev|training|playstore>
disable-model-invocation: true
---

# Mobile release build: $ARGUMENTS

`$ARGUMENTS` must be `dev`, `training` or `playstore`; anything else, ask. Run from the leapwell root, in order; stop on the first hard failure and show it verbatim. For the release checklist (notes, readiness, version PR) use `/lw-release mobile <version>`. **This skill builds artifacts only.** It never commits, pushes, merges, tags, creates releases or uploads to Play Console - those are human steps, say so in the report. Never print or commit `android/key.properties`, keystores or any `env.*.json` content.

1. **Clone.** `repos/uhis_lf_mobile` must exist (else `/lw-setup --only mobile`). Report branch and short SHA (`git -C repos/uhis_lf_mobile status -sb`). Do not switch branches or pull.

2. **Pick the flow** (all commands run in `repos/uhis_lf_mobile`; each env file is gitignored there and supplied by the team - if it is missing, stop):

   | Arg | Env file | Command | Output |
   |---|---|---|---|
   | `dev` | `env.staging.json` (dev/staging backend) | `scripts/build_apk.sh staging --release --app-flavor prod` | `build/app/outputs/flutter-apk/app-prod-release.apk` |
   | `training` | `env.training.json` | `scripts/build_apk.sh training --release --app-flavor training` | `build/app/outputs/flutter-apk/app-training-release.apk` |
   | `playstore` | `env.production.json` + `android/key.properties` | see step 3 | `.aab` from `scripts/release.sh`, plus a release APK |

   - `training` is the separately installable "LW Training" app (own `applicationId` with a `.training` suffix, own launcher name and icon). Add `--dart-define=SHOW_ENV_BANNER=true` to the command to show the "TRAINING BUILD" banner; `build_apk.sh` forwards extra arguments to `flutter build`. Check identity with `aapt dump badging <apk> | grep package`.
   - `dev` is the normal production-identity app pointed at the dev backend; for the distinct training app use `training`.
   - Always **release** (AOT) builds; never substitute `--debug`.
   - Copy the result so builds do not overwrite each other: `mkdir -p releases` and `cp <output> releases/app_release_<dev|training>_$(date +%y-%m-%d_%H-%M-%S).apk` (`releases/` is gitignored).

3. **playstore only.**
   1. Hard-fail (no debug-signing fallback) unless `android/key.properties` and `env.production.json` both exist.
   2. Show `grep '^version:' pubspec.yaml` and `git tag -l 'v*' --sort=-v:refname | head -5`. **Ask the user to confirm the exact target `X.Y.Z+N`** and the build number that is actually live on Play (the repo version has drifted from the live versionCode before); N must exceed every one of them. Never pick the number yourself.
   3. `scripts/release.sh production "<X.Y.Z+N>" --app-flavor prod` bumps `pubspec.yaml` in the working tree, builds the signed `.aab` (`build/app/outputs/bundle/prodRelease/app-prod-release.aab`), verifies its signature against the upload keystore (any mismatch is a hard stop) and archives a copy under `releases/`. If it cannot find a JDK 21 `keytool`, set `JAVA_HOME` to a JDK 21 and rerun. Report the printed SHA-256 fingerprint.
   4. `scripts/build_apk.sh production --release --app-flavor prod`, then zip `app-prod-release.apk` into `releases/app_release_production_v<X.Y.Z+N>_apk.zip`.
   5. Draft plain user-facing "what's new" bullets (no PR numbers or internal terms), at most 500 characters (`wc -m`), in `store_assets/release_notes/<X.Y.Z>_en-US.txt`; list what changed from `git log <last-live-tag>..HEAD --oneline --merges`. Bangla (`bn-BD`) only if the user asks.

4. **Freshness check (all flows).** A release APK/AAB can ship a stale compiled Dart library. Verify: `find lib -newer <artifact> -name '*.dart'` prints nothing, and `unzip -l <apk> | grep libapp.so` lists the library (for an `.aab`, `unzip -l <aab> | grep libapp.so`). If a source file is newer than the artifact or the library is missing, run `flutter clean` and rebuild (it re-downloads dependencies), then check again.

5. **Report** a table: flow, branch/SHA, build + size, signing (upload key vs debug-key fallback - `build.gradle.kts` falls back to the debug key silently when `key.properties` is absent, so state which one was used; a debug-signed build cannot update an upload-key install), freshness, copied-to path. Playstore adds version, fingerprint, release-notes path and character count.

6. **Hand-off, always.** Tell the user what is left for a human: commit the `pubspec.yaml` bump and notes through a PR (`/lw-pr mobile <N>`), merge it, tag `vX.Y.Z+N` on `main` (`scripts/release.sh production "" --tag`) and push the tag (which fires the repo's release workflow), and upload the `.aab` and notes in Play Console. No Play Console access exists here; never claim the release is live.
