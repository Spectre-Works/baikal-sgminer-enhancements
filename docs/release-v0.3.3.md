# v0.3.3 — SPECTRE WORKS LLC branding

The Cooling panel footer now reads **SPECTRE WORKS LLC — Baikal sgminer
enhancements v0.3.3**, followed by the live fan-control/Cooling panel description
and GitHub source, releases and documentation link. The “Modified software”
prefix is removed. The footer remains visible when telemetry is unavailable.

This is a branding-only UI update. Fan policy, API permissions, startup behavior,
firmware, clocks and pool configuration are unchanged. The executable and complete
corresponding miner source are byte-identical to v0.3.0 and retain their original
asset names. Previous releases are not overwritten.

## Install

Download `bkb-fan-and-cooling-unified-installer-v0.3.3.tar.gz` and `SHA256SUMS`.
Verify the bundle's outer checksum, extract outside the public web root, enter
`unified-installer-v0.3.3/`, and run `sha256sum -c INSTALLER-SHA256SUMS`.

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --check
```

On the supported ARMv7 Ubuntu 16.04 BK-B/Scripta controller, during an approved
maintenance window with webUI/configuration editors closed:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --install --allow-restart
```

The unified installer may restart mining and briefly pause cron; it preserves
pool configuration and existing valid saved cooling preferences. It creates a
private recovery backup and verifies readiness. See the [installer guide](unified-installer.md)
for supported platforms, refusal conditions, permission changes and rollback.

## Downloads and validation

Assets include the unified offline bundle, standalone v0.3.3 panel source
archive and installer, unchanged fan-only ARM executable and complete miner
source archive, documentation, historical miner build information and checksums.
The bundle includes licenses and corresponding source. GitHub's automatic
repository archive is not the full miner source; use the explicit miner source
archive. No private configuration, backups, firmware images or clock experiments
are included.

Frontend branding/link tests, eight startup-helper tests and twenty installer
tests (including actual pinned assets and simulated rollback) pass. The UI is
deployed and checked on the live BK-B before publication; complete installed
payloads are compared against the release without restarting mining. The
installer transaction/restart and preference restoration were validated on
8 October using the same unchanged installation logic.

Live rollback, full reboot, deliberate thermal/USB failure, physical RPM/airflow
and long-duration hardware qualification remain untested. The curve uses
hash-board temperatures, not controller CPU temperature; fan telemetry is command
acknowledgement, not measured RPM. The legacy webUI remains trusted-LAN-only.
