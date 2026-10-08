# v0.3.0 — Live fan control + webUI Cooling panel

Released 8 October 2026. Includes fixed live fan control, the existing automatic hottest-board governor, the Scripta Cooling panel and optional startup preference restoration. No clock/overclock API or firmware images are included.

## Assets

- `sgminer-baikal-bkb-fan-v0.3.0-armhf`: **byte-identical to the fan-only v0.2.0 binary**, SHA-256 `7ed2720baeba0bfccd7c48d9ba2ad57d760fbea22b28faf888694158f56c406e`. No miner recompile or extra driver change was required for the panel. Original version string remains `5.6.2-BK_cod3gen_MOD`.
- `sgminer-baikal-bkb-fan-v0.3.0-source.tar.gz`: complete corresponding miner source, byte-identical archive content to the v0.2.0 source asset, upstream `3cde8deca53f83ac65bc685b988166bd17930753` plus cumulative fan patch and documented BK-B requested startup default 400 MHz. Contains dependency sources/licenses and mock-USB tests.
- `bkb-cooling-panel-v0.3.0.tar.gz`: five new application source files, two integration patches, tests, GPL license and installation/release documentation. It does not contain stock dashboard replacements, private miner configurations, credentials, backups or firmware.
- `0002-automatic-baikal-fan-control.patch`, `automatic-fan-control.md`, `cooling-panel.md`, `release-v0.3.0.md`, `BUILD-INFO.txt` and `SHA256SUMS`.

GitHub's automatic source ZIP/tarball contains this enhancement repository, not the full upstream miner. Use the explicit miner source asset for the binary's corresponding source; the Cooling panel source is both committed to the repository and separately packaged.

## Installation / build

Verify `sha256sum -c SHA256SUMS` after downloading all listed assets (or verify relevant entries individually). Checksums prove asset consistency, not independent author identity. The legacy native ARMv7 hard-float executable targets the matching BK-B Ubuntu 16.04.2 environment, not ARM64, modern Pi OS or unidentified Baikal models. Inspect `file` and `ldd`; do not force incompatible libraries.

The miner binary/build/maintenance-window installation remains described in [v0.2.0](release-v0.2.0.md). Its startup defaults, legacy clock encoding, board-reported MHz and estimated hashrate are unchanged; these do not prove physical overclocking. Installing the miner requires a supervised stop/start and a recoverable backup. **Publishing this release does not deploy that binary to the live miner.**

The [Cooling panel guide](cooling-panel.md) describes minimal integration into the existing authenticated Scripta Status page, optional persistence, security, validation and rollback. No mining restart is needed for the panel when the compatible fan API is already installed. The helper starts conservatively at 100% on future miner starts, then restores an explicitly saved preference after telemetry becomes ready. Automatic is not made persistent by the miner binary alone.

The curve excludes Pi temperature. Acknowledged fan duty is not measured RPM or proof of fan rotation. Manual mode does not follow the curve, and a 10% UI minimum is not a universal safe-duty guarantee. Keep the legacy webUI on a trusted LAN; new endpoint protections do not harden unrelated legacy routes.

## Validation and known limits

Fan policy/mock-USB driver tests and panel frontend/startup/backend tests passed. The panel was deployed and validated on a live three-board BK-B: 100% Full Cooling, Automatic acknowledgement/timed step-down, saved preference reload, protected endpoint checks, continuing accepted work and preserved protocol clock/algorithm/cutoff state without a miner restart. The operator reported successful use. Full live dashboard validation used the existing protocol-compatible host build, not a deployment of the packaged fan-only binary.

Actual production restart/reboot restoration remains pending; startup behavior has simulated test coverage. No destructive fault injection or physical RPM/airflow test was performed live. Earlier v0.2.0 build provenance is retained and explicitly identified in BUILD-INFO. This is not a claim of a clean bit-for-bit reproducible build or broad hardware compatibility.

GPL-3.0 changes; upstream and bundled dependency notices are preserved with corresponding source. No experimental clock source or firmware asset is part of this release.
