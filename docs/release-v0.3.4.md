# v0.3.4 — Fan timestamp fix and visible runtime version

Automatic cooling could briefly request 100% at low temperatures because the
governor sampled time before taking the shared USB mutex. A board update while
it waited could receive a newer timestamp; unsigned age subtraction then wrapped
and falsely triggered the 15-second stale-telemetry failsafe. Time is now sampled
under the same mutex as board telemetry. A regression test enforces this order.
The genuine stale/invalid-data fallback, fault latch, temperature curve, delayed
step-down, clock selectors, algorithm and cutoff behavior are unchanged.

The miner now identifies itself as
`sgminer 5.6.2-BK_cod3gen_MOD-spectreworks-v0.3.4` in `--version` and the TUI.
The API `version` command and board stats expose enhancement version `0.3.4`.
The footer shows **Panel v0.3.4** separately from the live **Running miner**
version. Older binaries are explicitly unidentified; unavailable telemetry is
not presented as a current runtime identity. AGENTS.md and the consistency check
require versioning before future behavioral deployments.

## Downloads

- `sgminer-baikal-bkb-fan-v0.3.4-armhf`: native ARMv7 hard-float BK-B executable.
- `sgminer-baikal-bkb-fan-v0.3.4-source.tar.gz`: complete corresponding miner
  source, bundled dependency sources/licenses, version header and mock-USB tests.
- `bkb-cooling-panel-v0.3.4.tar.gz`: panel/startup sources, tests and integrations.
- `install-bkb-cooling.py`: installer pinned to this binary and panel archive.
- `bkb-fan-and-cooling-unified-installer-v0.3.4.tar.gz`: offline bundle containing
  installer, matching payloads, complete miner source, licenses and documentation.
- `0002-automatic-baikal-fan-control.patch`, implementation/installation guides,
  `BUILD-INFO.txt` and `SHA256SUMS`.

GitHub's automatic repository archive is not complete corresponding miner source;
use the explicitly named source asset. Earlier tags and assets remain unchanged.
No credentials, private configuration, backups, firmware or clock experiments
are included.

## Install and identify

Verify the outer `SHA256SUMS`, extract the offline bundle outside the web root,
enter `unified-installer-v0.3.4/` and verify `INSTALLER-SHA256SUMS`. Then:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --check
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --install --allow-restart
```

The second command authorizes a brief mining restart and watchdog pause. The
standard installer creates a private recovery backup; respect an operator's
explicit no-backup instruction through a reviewed deployment procedure instead.
See unified-installer.md for platform checks, backup handling and limitations.
Existing valid configuration/preferences are preserved. Hard-refresh Status and
check both panel and running miner versions, healthy boards and acknowledged fan
operation. Query the actual running `version`/`stats` API, not just a staged file's
`--version`; compare the running executable hash with SHA256SUMS.

## Build and validation scope

Built for the observed BK-B's ARMv7 Ubuntu 16.04 controller with GCC 5.4 and the
existing static Baikal USB library. Bundled USB source files matched the existing
native tree; that library was reused because a clean build encounters legacy
`LIBUSB_DESCRIBE`/`usbi_gettimeofday` errors. Build provenance and hashes are in
BUILD-INFO.txt. This is not a general ARM64/new-OS binary or a claim of fully
reproducible clean builds. The BK-B startup request remains 400 MHz; reported
480 MHz is controller telemetry, not measured physical overclocking.

The timestamp regression fails against the old driver and passes with the fix.
Native fan-policy/mock-USB, frontend, PHP backend, startup-helper and installer
checks cover the affected behavior, including actual pinned release assets.
Production validation checks the running version/checksum, three healthy boards,
unchanged option tuple, saved Automatic restoration, normal step-down and accepted
shares. Detailed observations are recorded in automatic-fan-control.md.

The earlier 100% incident's exact cause was not recoverable from retained logs;
this release fixes the independently confirmed timestamp race. Physical RPM,
fault injection, cold-start fan qualification and long-duration hardware safety
are not certified. Duty is command acknowledgement; the curve uses hash-board
temperatures. Keep the legacy webUI on a trusted LAN.
