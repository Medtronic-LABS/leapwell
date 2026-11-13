---
name: lw-coaching-android-build
description: Build and test the micro-coaching Android SDK (repos/spice-coaching-android) with its documented Gradle commands - SDK .aar, sample app, unit tests, publish to Maven Local.
argument-hint: "[sdk|app|test|local-publish]"
disable-model-invocation: true
---

# Micro-coaching Android SDK build

Repo: `spice-coaching-android` (key `coaching-android`, integration branch `leapwell-main`). Missing clone: `/lw-setup --only coaching-android`. Modules: `sdk-android/` (the library), `sdk-android-sherpa/` (optional offline Bengali speech-to-text), `app/` (sample app). Only the Gradle commands below are documented in its README; for lint, signing, CI details or the host-app integration (`docs/documentation/00-quick-start.md`), check the repo README and `CONTRIBUTING.md` instead of guessing. `repos.json` records no lint command for this repo.

`$ARGUMENTS` picks one task (default `sdk`); run in `repos/spice-coaching-android`:

| Task | Command |
|---|---|
| `sdk` | `./gradlew :sdk-android:assembleDebug` (SDK `.aar`) |
| `app` | `./gradlew :app:assembleDebug` (sample app) |
| `test` | `./gradlew :sdk-android:test` (unit tests) |
| `local-publish` | `./gradlew :sdk-android:publishToMavenLocal` (to `~/.m2`, for a host app such as the SPICE/LeapWell client to consume) |

Requirements from the README: min SDK 23, compile SDK 36, Kotlin 2.1.20, AGP 9.1.0, ABI `arm64-v8a` only - so run the sample app on an arm64 emulator or device. Installing the built sample APK: the README does not document it; locate the output under `app/build/outputs/` and use `adb install -r <apk>` after confirming the path with `ls`.

Never run `./gradlew :sdk-android:publish` (pushes to the configured remote repository) or change the SDK version fields; releases are a human step. Show Gradle errors verbatim; report which task passed or failed and the artifact path.
