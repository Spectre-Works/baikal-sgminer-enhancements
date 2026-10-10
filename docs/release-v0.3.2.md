# v0.3.2 — Visible modification identity

Released 9 October 2026. The Cooling panel now displays **Modified software:
Baikal sgminer enhancements v0.3.2**, describes the live fan-control/Cooling
panel modifications, and links to GitHub for source, releases and documentation.
Identification remains visible even when telemetry is unavailable. The link
does not load third-party resources until clicked.

No fan policy, clock, firmware, API permissions or pool configuration changes.
The fan-only miner executable and complete corresponding source archive are
byte-identical to the v0.3.0 release. Their original asset names are retained.
The version displayed in the panel identifies the enhancement/UI package, not
board firmware or the upstream miner version string.

## Install

Download `bkb-fan-and-cooling-unified-installer-v0.3.2.tar.gz` and `SHA256SUMS`
from this release. Verify the bundle's outer checksum, extract into a new
staging directory outside the web root, enter `unified-installer-v0.3.2/`, and
verify `sha256sum -c INSTALLER-SHA256SUMS`. Run checks first:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --check
```

On the supported ARMv7 Ubuntu 16.04 BK-B/Scripta system, during an approved
maintenance window with webUI/configuration editors closed:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --install --allow-restart
```

Install may restart mining and briefly pause cron. Private backups preserve
original application files, directory permissions and configuration for manual
recovery. Pool configuration is never rewritten. Existing saved fan preferences
are preserved. The installer is a no-op only when all files and permissions
already match. See [the full installer guide](unified-installer.md).

## Assets

- All-in-one offline bundle: updated panel source, installer, unchanged miner
  binary and complete corresponding miner source, licenses, guides and checksums.
- `bkb-cooling-panel-v0.3.2.tar.gz`: panel source, integration patches and tests.
- `install-bkb-cooling.py`, installer/release/identity guides and `SHA256SUMS`.
- Unchanged `sgminer-baikal-bkb-fan-v0.3.0-armhf` and
  `sgminer-baikal-bkb-fan-v0.3.0-source.tar.gz` as standalone assets.

GitHub's automatic repository source archive is not the complete miner source;
use the explicit miner source archive. Private configuration, recovery backups,
firmware images and clock experiments are excluded.

## Validation and limits

Frontend identity/link and controller tests, eight startup-helper tests and
twenty installer tests (including actual pinned assets and simulated rollback)
pass. The installer transaction/restart, released binary and saved Automatic
preference restoration were validated on the live BK-B on 8 October. The
v0.3.2 footer is validated on that miner before publication, with installed
payload hashes compared against this release.

Live rollback, deliberate thermal/USB faults, full reboot, physical RPM/airflow
and long-duration qualification were not performed. The governor uses hash-board
temperatures, not the controller CPU. Acknowledged duty is not measured RPM.
Reported clock/hashrate are not proof of effective overclocking. Keep the legacy
Scripta interface on a trusted LAN; this does not harden all legacy web routes.
