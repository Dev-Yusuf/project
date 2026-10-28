# Database credential remediation

Settings read database credentials from `DATABASE_URL`. Keep real values in the
ignored local `.env` file or the hosting provider's secret environment settings.
The `.env.example` file contains placeholders only.

## Rotate the exposed password

Treat the previously committed password as compromised even after removing it.
Identify whether the historical database account still exists. If it does,
rotate its password through the database provider or administrator. Rotate any
other accounts that reused that password. If the account is retired, confirm
that its credentials have been revoked.

Update `DATABASE_URL` for every affected deployment, worker, and local environment,
then restart affected services and verify database connectivity. Do not paste
credentials into chat, issue descriptions, command arguments, or commits.

## Remove the password from Git history

History cleanup is still pending. Two commits reachable in the local clone change
the occurrence of the exposed password in the settings file. Remote-only branches,
forks, pull request refs, and other clones have not been audited.

Coordinate a maintenance window with repository collaborators. Use a separate,
fresh mirror clone and `git-filter-repo` with a private replacement file to replace
the exposed password across all historical file contents. Include historical
bytecode and other binary files in verification. Keep the current working checkout
and its uncommitted changes intact.

Before publishing rewritten refs, scan every reachable blob for the old password,
review the changed refs, and confirm the rotated credentials work. Publishing the
rewritten history requires force-updating affected remote refs. Collaborators
should re-clone afterward so that old history is not reintroduced. Follow the Git
host's sensitive-data removal procedure for cached views and pull request refs.

Deleting the literal from the latest settings file does not revoke the credential
or remove it from earlier commits.

The historical `data.json` fixture also contains real account records, password
hashes, admin logs, and sessions. Its current version has been sanitized. Include
those records in the historical audit/removal process and revoke affected live
sessions; assess password resets for the exposed account hashes.
