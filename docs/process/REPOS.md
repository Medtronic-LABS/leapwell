# Repos

The seven LeapWell code repos, all under the `Medtronic-LABS` GitHub org. `repos.json` is the single source of
these facts (a test fails if this table drifts from it); correct integration branches there. `/lw-setup` clones
each into `repos/<name>` in the workspace. `leapfrog-ai-service` is private; the others are public.

| Key | Repo | Area | Stack | Integration branch | Verify (test / lint / build) | Notes |
|---|---|---|---|---|---|---|
| `mobile` | [uhis_lf_mobile](https://github.com/Medtronic-LABS/uhis_lf_mobile) | Mobile app | Flutter | `develop` | `flutter test` / `flutter analyze` / `flutter build apk --debug` | |
| `core` | [frappe_spice_next_core](https://github.com/Medtronic-LABS/frappe_spice_next_core) | Frappe apps | Frappe (Python) | `main` | `bench --site {site} run-tests --app spice_next_core` / `ruff check spice_next_core/` / `bench build --app spice_next_core` | needs the frappe env (`env/frappe`); site from `env/frappe/.env` |
| `shukhee` | [leapwell_shukhee_integration](https://github.com/Medtronic-LABS/leapwell_shukhee_integration) | Frappe apps | Frappe (Python) | `main` | `bench --site {site} run-tests --app shukhee_integration` / `ruff check .` / `bench build --app shukhee_integration` | needs the frappe env (`env/frappe`); site from `env/frappe/.env` |
| `ai` | [leapfrog-ai-service](https://github.com/Medtronic-LABS/leapfrog-ai-service) | AI Scribe | Python FastAPI | `develop` | `pytest -q` / `ruff check .` / none | no build step |
| `coaching` | [spice-coaching](https://github.com/Medtronic-LABS/spice-coaching) | Micro-coaching | Python | `development` | `python -m pytest` / `ruff check .` / none | no build step |
| `coaching-android` | [spice-coaching-android](https://github.com/Medtronic-LABS/spice-coaching-android) | Micro-coaching | Kotlin | `development` | `./gradlew :sdk-android:test` / none / `./gradlew :sdk-android:assembleDebug` | lint not documented - check README |
| `coaching-dashboard` | [spice-coaching-dashboard-ui](https://github.com/Medtronic-LABS/spice-coaching-dashboard-ui) | Micro-coaching | TypeScript/Vite | `develop` | `npm run test -- --run` / `npm run lint` / `npm run build` | |

`{site}` is the Frappe site name from `env/frappe/.env`. The Frappe repos run their checks inside the bench
(`env/frappe/README.md`). Each repo's branch protection, own build/test CI and extra tooling stay the repo's own;
leapwell adds only the thin layer from `templates/repo-layer/` (`lw-pr-check`, `lw-secret-scan`, `lw-close-on-merge`, `lw-lint`, PR
template, `CODEOWNERS`, issue-chooser pointer, `CLAUDE.md` section). Each repo has an `area:<key>` label in leapwell.

Product areas and the repos behind them are in the Wiki page `Repos-and-Areas` (seed: `wiki/Repos-and-Areas.md`).
