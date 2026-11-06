---
name: lw-mobile-start
description: Build the LeapWell Flutter app (repos/uhis_lf_mobile) as a debug APK, install it on an emulator or connected device and launch it. Incremental rebuild - use lw-mobile-fresh-launch for a clean slate.
disable-model-invocation: true
---

# Build, install and launch the mobile app

Run every step in order from the leapwell root. Show failures verbatim; never retry silently. The repo facts (`verify`, `notes`) are in `repos.json` under `mobile`.

1. **Clone and config.**
   - `repos/uhis_lf_mobile` must be a git clone; otherwise tell the user to run `/lw-setup --only mobile`.
   - `repos/uhis_lf_mobile/env.development.json` must exist (gitignored; copy `env.example.json` and fill it in - the team supplies the values). If it is missing, stop and say so. Never print its contents or put its values into commands, issues, PRs or reports. Optional keys such as `AI_SERVICE_URL` also live in that file.

2. **State.** `git -C repos/uhis_lf_mobile status -sb` and `git -C repos/uhis_lf_mobile rev-parse --short HEAD`. Report the branch and SHA. Do not pull, rebase or switch branches here; if the user wants the latest, `git -C repos/uhis_lf_mobile pull --ff-only` on a clean branch, and stop on divergence.

3. **Dependencies.** In `repos/uhis_lf_mobile`: `flutter pub get`. If `pubspec.yaml` mentions `build_runner`: `dart run build_runner build --delete-conflicting-outputs`.

4. **Build** (in `repos/uhis_lf_mobile`): `scripts/build_apk.sh development`. The script reads `env.development.json` and builds the `prod` product flavor in debug mode. Output: `build/app/outputs/flutter-apk/app-prod-debug.apk` (flavor-qualified; confirm with `ls -lh build/app/outputs/flutter-apk/`).

5. **Device.** `adb devices`. Use a listed emulator or phone. If none: `emulator -list-avds`, start the first AVD in the background (`nohup emulator -avd <name> -no-snapshot-load > "${TMPDIR:-/tmp}/lw-emulator.log" 2>&1 &`), then `adb wait-for-device` and poll `adb shell getprop sys.boot_completed` until it prints `1`. No AVD: create one in Android Studio (Device Manager). Apple Silicon needs an ARM64 AVD image.

6. **Install.** `adb install -r build/app/outputs/flutter-apk/app-prod-debug.apk` (`-r` keeps app data; never add flags that delete data).

7. **Launch and verify.** Resolve the package from `android/app/build.gradle.kts` (`applicationId`, currently `com.medtroniclabs.uhis_next`):
   ```
   PKG=$(grep -E '^[[:space:]]*applicationId' repos/uhis_lf_mobile/android/app/build.gradle* | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
   adb shell am start -n "$PKG/.MainActivity"
   ```
   (`monkey` is unreliable on this emulator.) After 3 seconds `adb shell pidof "$PKG"`. If it is not running, show `adb logcat -d -t 200 | grep -E 'FlutterActivity|AndroidRuntime|System.err|flutter' | tail -60`.

8. **Report** a table (Branch/SHA, Deps, Build + APK size, Device, Install, Launch + PID) and end with `App: RUNNING` or `App: NOT-RUNNING (<reason>)`.

For an attached debug session use `flutter run --dart-define-from-file=env.development.json -d <device-id>` in `repos/uhis_lf_mobile` (foreground; the skill does not return until the user quits).
