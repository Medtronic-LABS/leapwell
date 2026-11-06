---
name: lw-ai-test
description: Run the pytest suite (and optionally ruff) of the AI Scribe service (repos/leapfrog-ai-service). Needs no running stack, network or real provider keys.
argument-hint: "[pytest args]"
disable-model-invocation: true
---

# AI Scribe tests

Commands come from `repos.json` (`ai`: `verify.test` = `pytest -q`, `verify.lint` = `ruff check .`, no build step). The suite uses in-memory SQLite and mocked storage and Redis (`conftest.py`), so it needs no containers, no internet and no keys; `pytest.ini` sets `testpaths = tests`.

1. If `repos/leapfrog-ai-service` is missing, point to `/lw-setup --only ai`.
2. Use a virtual environment: if none is active, create one inside the repo directory (`python3 -m venv .venv`, gitignored by the repo's own rules - check `git status` stays clean) and activate it. Install on first use: `pip install -r requirements.txt` (plus the repo's dev requirements if its README names them).
3. In `repos/leapfrog-ai-service` run `pytest -q $ARGUMENTS` (for a single area: `pytest tests/test_<feature>.py -q`). Add `-v --tb=short` when debugging a failure.
4. On request (or before a PR) also run `ruff check .`.
5. Report pass / fail / skipped counts and, per failure, the test id and the one-line cause. Do not edit tests to make them pass; a failure that looks environmental (missing system library such as ffmpeg or libsndfile) is reported as such. Never print `.env` values.
