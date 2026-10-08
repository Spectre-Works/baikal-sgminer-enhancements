# v0.3.1 — Unified installer preview

Released 8 October 2026 as a **prerelease**. v0.3.0 remains the latest stable release. This adds a unified offline installer for the unchanged v0.3.0 live/automatic fan-control miner, Scripta Cooling panel and startup helper. No miner recompilation, clock experiments, firmware images or live deployment are included in this publication.

## Download and start

Download `bkb-fan-and-cooling-unified-installer-v0.3.1.tar.gz` and the outer `SHA256SUMS` from this release, into a fresh staging directory outside the public web root. The outer manifest also covers the standalone installer and guides: download all listed assets for a full `sha256sum -c SHA256SUMS`, or verify the bundle entry individually. Checksums establish consistency, not independent author identity; use the trusted repository.

Extract the bundle and enter `unified-installer-v0.3.1/`. It includes the executable, complete corresponding miner source archive, panel source archive, licenses, installer and guide. Verify `sha256sum -c INSTALLER-SHA256SUMS` there. Its inner `SHA256SUMS` belongs to the unchanged v0.3.0 payloads; do not replace it with the outer release manifest.

Run checks first on the verified physical BK-B controller:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --check
```

After reviewing the checks, schedule a supervised maintenance window and stop using the webUI/configuration editors while running:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --install --allow-restart
```

This explicitly authorizes a mining stop/start and temporary pause of the existing cron service. It backs up the original files privately, preserves pool configuration and valid existing preferences, integrates only recognized Scripta layouts, starts at conservative 100% duty, and confirms the selected preference through the fan API. First installations default to Automatic; existing preferences are preserved unless an override is requested. See [the full guide](unified-installer.md) for compatibility, directory-permission changes, refusal conditions, failure handling and rollback.

## Assets

- `bkb-fan-and-cooling-unified-installer-v0.3.1.tar.gz`: all-in-one offline bundle, including the unchanged v0.3.0 fan-only ARMv7 hard-float binary and complete corresponding source, Cooling panel source, installer, instructions, licenses and internal checksums.
- `install-bkb-cooling.py`: standalone installer source; requires the original v0.3.0 binary, panel archive and manifest alongside it or in the `--assets` directory.
- `unified-installer.md`, `release-v0.3.1.md`, `SHA256SUMS`: guides and outer checksums.

Installer source, 20 offline tests and documentation are also committed in the tagged repository. GitHub's automatic source archive is the enhancement repository, not the full miner source; the explicit miner source archive inside the bundle is the binary's corresponding source.

## Validation limits

Twenty offline installer tests pass, including a transaction/rollback simulation with the actual pinned assets, interrupted/failing stop, partial write failure, validation failure, corrupt backup, edited files, preference preservation, configuration-change protection and watchdog restoration failures. Existing startup and frontend tests pass; Python 3.5 grammar compatibility is checked.

The previously deployed panel and fan behavior were validated live and reported working by the operator. **The new combined installer has not yet completed a live installation/restart/rollback maintenance cycle.** Read-only target-platform compatibility checks, physical cooling qualification and live failure behavior still need supervised validation. It is not a universal Baikal installer. Only the inspected ARMv7 Ubuntu 16.04 BK-B/Scripta layout is supported, with an explicit operator model confirmation.

No guarantee covers power failure, SIGKILL, storage failure or unavailable hardware communication. Keep a recovery access path and retain the private printed backup. The script attempts recovery on ordinary failures and reports unconfirmed readiness or cron restoration failures instead of claiming success. Legacy webUI security limits remain: trusted LAN only. Board temperature drives the curve, not Pi temperature; acknowledged duty is not measured RPM.
