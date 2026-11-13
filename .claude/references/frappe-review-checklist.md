# Frappe review checklist

Read by `lw-reviewer` for diffs in the Frappe repos (`core`, `shukhee`). The defects that actually recur:

## Permissions and endpoints
- `@frappe.whitelist()` without an explicit permission check on the record it touches (`frappe.has_permission` / `doc.check_permission`).
- `allow_guest=True` without its own authentication, rate limit (`frappe.rate_limiter.rate_limit`) and input validation.
- `ignore_permissions=True`, or `frappe.get_all` (skips permissions) where `frappe.get_list` was needed.
- Trusting client-supplied identity, scope, role, record names, room names or storage keys.

## Queries
- `frappe.db.sql` with string formatting; user-controlled `doctype` / `fieldname` / `order_by`.
- N+1 queries in loops; unbounded `get_all` / `get_list` without `limit`.
- Raw SQL that only works on one engine when the site may run MariaDB or PostgreSQL - prefer `frappe.qb`.
- Slow work running in the request instead of `frappe.enqueue` (`long` queue for slow jobs).

## DocTypes, hooks and patches
- Changed DocType JSON: permissions table, `autoname`, `track_changes`, secrets stored in `Data` instead of `Password` fields.
- `doc_events` doing slow or external I/O synchronously.
- `after_migrate` that is not idempotent; patches missing from `patches.txt` or not re-runnable.

## Secrets and PHI
- Hardcoded keys / URLs; secrets or tokens in logs, URLs, error messages or realtime payloads.
- Patient names, identifiers or clinical text in logs, URLs, object-storage paths, error messages, browser console or third-party calls.
- Consent captured with policy version + timestamp + identity; access to recordings / documents audited; retention and deletion paths exist.

## Frontend and errors
- Hardcoded user-facing strings (use the app's strings module); `frappe.call` results rendered without `frappe.utils.escape_html`; secrets in JS.
- Bare `except:` / `except Exception: pass`; raw tracebacks shown to users.

## Tests
- New public behaviour ships with tests (`FrappeTestCase`), including permission-denied and guest cases.
- Unit tests never need external services (LLMs, media servers, S3, SMS, webhooks) - they are mocked.
