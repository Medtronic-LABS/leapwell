---
name: lw-mobile-e2e
description: Run the Playwright end-to-end suite of the LeapWell Flutter app (repos/uhis_lf_mobile/e2e) against a Flutter web build, headed, and summarise the result. Runs tests only; adds tests only when asked.
argument-hint: "[spec file or grep]"
disable-model-invocation: true
---

# Mobile web E2E (Playwright)

The suite lives in `repos/uhis_lf_mobile/e2e/` and drives the Flutter **web** build through its semantics tree (`flt-glass-pane`, ARIA roles). The repo README section "End-to-End Tests" is the authority; this skill runs it. `$ARGUMENTS` optionally narrows the run (a file under `e2e/tests/` or a `-g` pattern).

1. **Preconditions.** `repos/uhis_lf_mobile` is a clone (else `/lw-setup --only mobile`), `flutter config` has web enabled (`flutter config --enable-web` if not), and a gitignored env file whose `API_BASE_URL` the browser can reach exists (README: use a dedicated one for web, e.g. `env.e2e.json`, copied from `env.example.json`). Never print env values.

2. **Build and serve** (in `repos/uhis_lf_mobile`):
   ```
   flutter pub get
   flutter build web --dart-define-from-file=env.e2e.json
   (cd build/web && python3 -m http.server 5050 --bind localhost) &
   curl -fsS http://localhost:5050 > /dev/null
   ```
   Port 5050 is what `e2e/playwright.config.ts` expects (override with `LF_MOBILE_BASE_URL`). Remember the server's PID and stop it at the end.

3. **Credentials.** The specs read `LF_API_BASE_URL`, `LF_HASH_KEY`, `LF_USER`, `LF_PASS` from the environment. Take them from the env file the user points to or ask the user to export them in their shell; never echo, log or write them anywhere.

4. **Run, headed** (in `repos/uhis_lf_mobile/e2e`):
   ```
   npm install
   npx playwright install chromium
   npx playwright test --headed $ARGUMENTS
   ```
   Always headed; if there is no display, say so and stop instead of switching to headless. Artifacts (traces, screenshots, videos) land in `e2e/test-results/` and `e2e/report/` and must stay uncommitted.

5. **Report.** `npx playwright show-report report` is optional. Give a table: total, passed, failed (with spec names), flaky, duration, report path. If more than 30% fail, stop and say it looks like an environment problem (stale web build, backend unreachable, wrong credentials) rather than a regression. List routes in `lib/app/router.dart` with no spec under `e2e/tests/` as a coverage note.

6. End with `E2E: GREEN`, `E2E: RED (<n> failed)` or `E2E: NO-TESTS (<reason>)`.

Rules: never delete or overwrite existing specs; add a spec only when the user asks, one file per flow, selectors only from the rendered semantics tree (no invented selectors - if a widget has no `Semantics` label, say so); stop the web server you started.
