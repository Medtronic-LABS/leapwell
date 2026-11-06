#!/usr/bin/env bash
# Apply branch protection to leapwell main. Dry-run by default.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

usage() {
  cat <<USAGE
Usage: scripts/github/protect_branches.sh [--apply] [--help]

Protects main of $OWNER/$REPO:
  1 approval, CODEOWNERS review, dismiss stale reviews, strict required checks
  Required checks: pr-check, sdlc-scripts, lint, secret-scan, mockup-scan
  No force push, no deletion, conversation resolution required, enforce_admins false.
Code repos are protected by their own owners; this script only touches the tracker.
Default is a dry-run that only prints the gh api call and body.
USAGE
}

parse_common_flags usage "$@"
reject_unknown_args
banner

CHECKS='["pr-check", "sdlc-scripts", "lint", "secret-scan", "mockup-scan"]'

protection_body() {
  cat <<JSON
{
  "required_status_checks": { "strict": true, "contexts": $CHECKS },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "require_code_owner_reviews": true,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
}

run_stdin "$(protection_body)" \
  gh api -X PUT "repos/$OWNER/$REPO/branches/main/protection" --input -
