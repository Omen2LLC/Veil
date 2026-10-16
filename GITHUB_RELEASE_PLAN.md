# Veil GitHub release plan

- The authenticated GitHub login is `Omen2LLC`, a user account, not an
  organization. `Omen2LLC/Veil` did not exist when checked on 2026-10-15.
- The existing development Git history stays local. A separate curated source
  repository is prepared from the beta runtime; private backup files, session
  recovery, logs, screenshots, media, installers and secrets are excluded.
- `outputs/GitHub-Release-Prep` contains 15 historical tags from v0.84-preview
  through v0.93-beta-r7, plus v0.94-beta and v0.95-beta. Each has release notes and SHA-256
  checksums. The original ZIPs remain untouched. Most historical ZIPs are
  source-based Windows packages and still require Python; only the later
  standalone builds bundle Python. No missing standalone build has been
  recreated or relabeled. v0.93-beta-r5 has no
  recoverable distributable ZIP and must not be reconstructed or labeled as one.
- All 17 local archival tags have been checked: every tagged source file is
  byte-for-byte identical to its sanitized source ZIP. Historical beta revision
  tags retain the original internal `v0.93-beta` version string. The recovery
  commits use today's recovery date, not invented publication dates.
- An unused historical project/footage preview was removed from 12 prepared
  assets. Its original local archives are preserved. No user projects or media
  are included in the clean source repository.
- Actual native Apply/Restore passed on Studio 21.1.1.10 with generated test
  data, and the compiled local updater fixture passed. The release build gate
  requires fresh official Windows Studio metadata and matching native evidence
  for each new Veil version. It blocks untested future Resolve builds.
- Stable in-app update checks use the public GitHub Releases endpoint and
  require a matching Windows ZIP plus `SHA256SUMS.txt`. A private repository
  cannot provide this unauthenticated friend experience. Do not embed a GitHub
  credential in Veil or its packages. If the repository must stay private,
  keep automatic checks disabled until an authenticated distribution design is
  agreed and tested.
- The updater's disposable local ZIP/checksum/install/rollback tests do not
  constitute a live GitHub upgrade. Publish a stable release only after the
  exact Resolve build is supported and native Apply/Restore have been tested.

Release steps: inspect Blackmagic support; run offline and native compatibility
checks; verify the package with Python absent from `PATH`; inspect all assets
for private files; generate SHA256SUMS; test an update from the previous
release in a disposable installation; then publish release notes, source ZIP,
Windows ZIP and checksums. Preserve historical tags and never force-push them.

Publishing remains pending: the connected GitHub integration cannot create a
repository or upload Release assets. The official portable GitHub CLI is staged
and checksum-verified, but it needs a separate sign-in. No browser or sign-in is
opened while the user is gaming. `publish_release_plan.py` defaults to an offline
review and requires explicit visibility plus `--execute` before remote changes.
