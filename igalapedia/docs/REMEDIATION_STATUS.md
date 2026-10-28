# Remediation and deployment notes

## Implemented locally

- Removed inactive database credentials; database configuration uses `DATABASE_URL`.
- Sanitized blog submissions and historical rendering. History and Hall of Fame
  rendering and editors use the same rich-text policy. Inline styles and embedded
  active content are intentionally removed.
- Validated login and guidelines redirects against the current host and scheme.
- Made dictionary and history approvals transactional; locked and reloaded reviewed
  submissions. Notification callbacks wait for dictionary approval commits.
- Added collision-safe, length-limited dictionary slugs without changing existing URLs.
- Moved mixed-feed ordering and pagination into SQL; only page content is fetched.
- Enforced blog visibility on likes, comments, and reports.
- Made registration atomic and logout POST-only with a CSRF-protected navigation form.
- Escaped related-term HTML and added upload type, signature, and size validation.
- Made Supabase bucket and public URL configurable and URL-encoded media paths.
- Validated book-request email and message input, logged email errors, and stopped
  claiming notification success when delivery fails.
- Disallowed public download references on request-only books. Authors share these
  books privately after receiving a request; this is not a private file-download service.
- Rebuilt contribution counts from submissions and replaced leaderboard per-user
  lookups with one aggregate query. History approval no longer increments stale counters.
- Replaced silent failures in key submission, content-count, and email paths with
  diagnostics or normal error propagation. Users do not see raw database errors.
- Enabled secure production cookies, HTTPS redirect, short-duration HSTS, and a
  Render secret-key check. Render cannot enable debug mode. HSTS subdomains are
  opt-in and preload remains disabled, so deployment checks report those warnings.
- Added isolated test settings, regression coverage, SQLite/PostgreSQL CI, setup
  instructions, and ignore rules. Generated files remain on disk but are untracked.
- Removed user sessions/admin logs from `data.json`; fixture users are anonymized,
  inactive, nonstaff accounts with unusable passwords.
- Removed the duplicate lowercase README index entry that conflicted on Windows.

## Local validation

- The initial 49-test remediation suite passed with the pinned dependencies, including Django 5.0.3, using
  isolated SQLite, in-memory file storage, and a local email outbox.
- Migration state checks pass; the five new validation migrations apply in tests.
- All 93 project Python files parse. Working-tree and staged whitespace checks pass.
- Static source collection rebuilds 1,414 files. Production manifest hashing and
  gzip compression pass. Optional host-installed Brotli was disabled for the gzip
  check, matching the declared dependency set; a full Brotli build was not verified.
- Production settings checks with an ephemeral strong secret report only W005 and
  W021 for HSTS subdomains/preload. No production secrets or services were used.
- The sanitized fixture loads successfully without usable accounts or sessions.
- No bytecode/collected static files or case-conflicting paths remain tracked.

## Before deploying

The configured session pooler on port 5432 returned tenant/user-not-found during
connectivity diagnosis, while the same project's transaction pooler on 6543 passed
a read-only connectivity check with the existing credentials. The local ignored
`.env` now uses port 6543. Settings automatically disable server-side cursors and
persistent Django connections for Supabase transaction poolers. If the deployed
service has the same session-pooler failure, update its `DATABASE_URL` to port 6543
and deploy these settings; the Render environment was not changed locally.
The corrected connection also passed `SELECT 1` through Django in the project's
virtual environment, and all 50 tests pass there, including the pooler settings
regression test. No live data or database schema was changed by these checks.

1. Configure `SUPABASE_URL`, storage credentials, bucket, region, and S3 endpoint in
   Render. Alternatively set `SUPABASE_PUBLIC_MEDIA_URL` for your CDN. There is no
   hardcoded fallback to a particular Supabase project anymore.
2. Set a long random `SECRET_KEY`, `DEBUG=False`, custom-domain `ALLOWED_HOSTS`, and
   custom HTTPS `CSRF_TRUSTED_ORIGINS`. Preserve the current strong secret unless
   intentionally rotating it: changing it signs users out and invalidates signed data.
3. Back up the production database through its provider. Review and apply the five
   upload-validator migrations. They update model validation state, not stored files.
4. Run tests and migration checks. Deploy through the existing Render process, then
   verify login/logout, moderation, feed, media, and a book request on the live site.
5. Verify SMTP access on the selected Render compute plan or use an HTTPS-based
   transactional mail backend. Local tests do not prove external email delivery.

## Operational work still pending

- Rotate/revoke the historically exposed database credentials and any reused
  passwords. See [credential remediation](DATABASE_CREDENTIAL_REMEDIATION.md).
- The old fixture in Git history contains real account password hashes, identity
  fields, and sessions. Assess affected users, revoke exposed sessions, and require
  password resets as appropriate. Include these fixture records in history cleanup;
  replacing the current file does not erase copies from history or forks.
- Audit existing request-only books for files already stored in public buckets.
  Hiding a URL or clearing a database field cannot make a public object private.
  Remove exposed objects or relocate them to truly private storage at the provider.
  Existing uploaded files have not been inspected or deleted by this change.
- Review backups, database plan expiry, service uptime, and dependency security
  maintenance separately. Existing Django/CKEditor versions were not upgraded by
  this remediation pass. Upload checks are not antivirus scanning.
- CI configuration has been added but has not run remotely. SQLite tests do not
  prove PostgreSQL concurrency behavior or the provider's permissions.
- No commits, pushes, force pushes, production migrations, or deployments have
  been performed. Repository-history rewriting still requires coordination.
