# Scripta Cooling panel

See [installation, validation and rollback](../docs/cooling-panel.md) and the [v0.3.0 release guide](../docs/release-v0.3.0.md).

The [v0.3.1 unified installer preview](../docs/unified-installer.md) installs the unchanged v0.3.0 miner, panel and startup helper together, with checks, explicit restart approval, private backups and recovery. It is a prerelease with offline test coverage, not yet validated through a live install/rollback cycle.

`package/web/` contains four new fan-only web files. `package/startup/` contains the optional once-per-process startup helper. The two integration patches add the controller/card to existing Scripta files and optionally add conservative startup plus preference restoration. They do not replace a customized dashboard or startup script wholesale.

Tests are development-only: **never copy tests or router.php into the installed web root**. The isolated test router deliberately creates a test login and must not be publicly exposed.

Source changes in this directory are GPL-3.0 under the repository LICENSE. No private miner configuration, firmware images, production backup, credentials or clock experiments are included.
