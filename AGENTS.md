# Baikal sgminer enhancements

Read README.md and the relevant docs before editing. This repository contains
cumulative patches, the Cooling panel and the offline unified installer; it is
not the full upstream miner source tree. Preserve the documented upstream base,
BK-B default clock request and fan-only scope. Inspect Git status/remotes first.

## Versioning and releases

- Every deployed behavior change needs a new enhancement version **before**
  deployment. Never identify a deployed change only by its checksum or commit.
  Use the next unused semantic version; never overwrite a published tag/asset.
- VERSION is the release version. Keep the patched SPECTRE_WORKS_VERSION macro,
  CLI/startup/TUI and API version strings, panel version, installer identity,
  asset filenames, pins, tests and current documentation consistent with it.
  Preserve the upstream miner version as a prefix; distinguish enhancement,
  panel and hardware/firmware identities. The panel must show the running
  miner's reported enhancement version, or explicitly say it is unidentified
  or unavailable. Never infer the running binary's version from a static label.
- Run tools/check-release-version.py, the native miner regression/mock-USB
  suite, frontend/backend/startup tests and installer tests with actual pinned
  assets. The timestamp-order regression must fail against the unfixed driver.
  Verify patch application against the documented clean upstream commit.
- Before deployment, verify ARM format, resolved dependencies and exact
  --version output. After restart, query the **running** API version and stats,
  verify /proc/PID/exe checksum against the release artifact, and check all
  three boards, fresh telemetry, acknowledged fan operation, unchanged option
  selectors/mode/cutoff and continued accepted shares. A checksum supplements
  the visible version; it does not replace it.
- Publish the exact tested/deployed binary, complete corresponding miner source
  including bundled dependencies/licenses, panel, pinned installer, offline
  bundle, build provenance, release notes and SHA256SUMS. GitHub's automatic
  repository source archive is not complete corresponding miner source.
  Record reused dependency artifacts and build limitations accurately.
- Commit/push release metadata and tag the exact release commit. Upload/check
  all assets before publishing a GitHub release; verify the published tag,
  release status, filenames and asset digests. Report the release URL.

## Production operations

Local checks do not authorize a production restart or publication; follow the
user's deployment scope. Current session authorization can provide that scope.
Respect explicit backup/rollback preferences; do not create a rollback copy
when the operator has declined one. Pause and restore the existing restart
watchdog around an authorized replacement, preserve configuration/preferences,
and use acknowledged full cooling during restart. Never run two miners against
the controller. Do not flash firmware or add clock-control behavior for a fan fix.

Do not commit credentials, pool configurations, backups, logs containing private
data or generated binaries. Keep operational validation in docs with its exact
unit/time scope. Acknowledged fan duty is not RPM or physical airflow evidence.
