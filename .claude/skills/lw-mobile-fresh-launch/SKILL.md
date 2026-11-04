---
name: lw-mobile-fresh-launch
description: Clean build of the LeapWell Flutter app (repos/uhis_lf_mobile), uninstall the old install, then install and launch it on an emulator or device. Use when the running app shows stale state.
disable-model-invocation: true
---

# Clean build, reinstall and launch

For a normal incremental rebuild use `/lw-mobile-start`. Run every step in order from the leapwell root; show failures verbatim; never retry silently.

1. **Clone and config.** `repos/uhis_lf_mobile` must be a git clone (else `/lw-setup --only mobile`) and `repos/uhis_lf_mobile/env.development.json` must exist (gitignored; the team supplies the values). Never print its contents.

2. **Clean.** In `repos/uhis_lf_mobile`: `flutter clean`, then `flutter pub get`. (A clean forces dependency re-downloads; that is expected.)

3. **Build.** `scripts/build_apk.sh development` in `repos/uhis_lf_mobile`. Output `build/app/outputs/flutter-apk/app-prod-debug.apk`; report `ls -lh` of it.

4. **Device.** `adb devices`; use a listed emulator or phone, otherwise start an AVD exactly as in `/lw-mobile-start` step 5.

5. **Uninstall the old app** (only this app's package, so no stale DB schema or cached token survives):
   ```
   PKG=$(grep -E '^[[:space:]]*applicationId' repos/uhis_lf_mobile/android/app/build.gradle* | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
   adb uninstall "$PKG" || echo "not installed - skipping"
   ```

6. **Install** (fresh, no `-r`): `adb install repos/uhis_lf_mobile/build/app/outputs/flutter-apk/app-prod-debug.apk`

7. **Launch.** `adb shell am start -n "$PKG/.MainActivity"`, wait 3 seconds, `adb shell pidof "$PKG"`. On failure show `adb logcat -d -t 200 | grep -E 'FlutterActivity|AndroidRuntime|System.err|flutter' | tail -40`. Do not use `monkey` (it exits without starting the activity on this emulator).

8. **Report** (Clean, Build + size, Device, Uninstall, Install, Launch + PID) and end with `App: RUNNING` or `App: NOT-RUNNING (<reason>)`.

Never wipe device data beyond this app's own package.
