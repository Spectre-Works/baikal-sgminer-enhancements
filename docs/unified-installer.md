# Unified BK-B fan-control + Cooling panel installer — v0.3.3

This installer installs the **unchanged v0.3.0 fan-only miner binary, v0.3.3 Cooling panel and startup preference helper together**. It needs Python 3.5+ on the matching ARMv7 Ubuntu 16.04 BK-B/Scripta controller. It deliberately does not support unidentified models, ARM64 or modern Pi operating systems. No firmware is flashed, no clock API is added, and pool configuration is never rewritten.

Status: [v0.3.3 release](https://github.com/Spectre-Works/baikal-sgminer-enhancements/releases/tag/v0.3.3). The installer transaction, binary replacement/restart and saved preference restoration completed on the live BK-B on 8 October using v0.3.1. This version only updates panel identification and release asset pins. Live rollback, full reboot and physical fault qualification remain untested; do not treat simulated failure coverage as hardware qualification.

## Simple installation

Download `bkb-fan-and-cooling-unified-installer-v0.3.3.tar.gz` from the v0.3.3 release. Verify the outer release checksum manifest, then extract it into a new staging directory outside `/var/www` and enter `unified-installer-v0.3.3/`. It contains the installer, pinned payloads, complete miner source, licenses and these instructions. Do not copy the whole directory into the web root.

For the all-in-one bundle, verify all staged files with `sha256sum -c INSTALLER-SHA256SUMS` before running anything. The internal `SHA256SUMS` covers this bundle's payloads; do not overwrite it with the outer release manifest. The installer checks the exact two required asset hashes whether you use the bundle or individual downloads.

Alternatively, put `install-bkb-cooling.py` beside these three files from the trusted [v0.3.3 release](https://github.com/Spectre-Works/baikal-sgminer-enhancements/releases/tag/v0.3.3):

- `sgminer-baikal-bkb-fan-v0.3.0-armhf`
- `bkb-cooling-panel-v0.3.3.tar.gz`
- `SHA256SUMS`

The miner source archive is also available in that release; no compilation is required for installation. Download from the trusted repository, inspect the installer, and retain backups outside the public web directory. Checksums establish consistency, not independent author identity. The installer additionally pins the exact binary and panel archive hashes and does not download or run arbitrary remote scripts.

From the staging directory, run the preview first:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --check
```

This checks the assets, platform, running miner identity, three healthy boards below 51°C, dependencies, existing Scripta integration, JSON configuration, startup script and source syntax. It writes only private temporary check files, not production files or fan settings. `--confirm-bkb` means the operator has verified the physical model; the API alone cannot prove that identity.

During an approved maintenance window, **stop using the webUI, configuration editors and other mining-control tools**, then run:

```sh
sudo python3 ./install-bkb-cooling.py --assets . --confirm-bkb --install --allow-restart
```

This is the combined install command. It explicitly authorizes a mining stop/start and a temporary pause of the existing cron service to prevent its miner watchdog racing the installation. Other scheduled jobs are also paused briefly. Cron must initially be running. The installer is offline; it does not install missing system packages or broaden API/network permissions.

Default behavior preserves an existing valid saved cooling preference. On a first installation, it saves Automatic mode. To deliberately choose a different preference, append `--startup-mode auto` or `--startup-mode manual100` (Manual 100%). Corrupt saved preferences are rejected rather than silently replaced. Apply/Save semantics in the panel remain unchanged.

After success, open the miner's existing Status page and hard-refresh. Verify all three boards, Cooling status, requested/acknowledged duty, temperatures and continued accepted shares. Duty is not measured RPM. The curve uses hash-board temperatures, not the Pi temperature. Keep Scripta on a trusted LAN.

## What the installer does

1. Checks the pinned v0.3.0 binary and v0.3.3 panel archive and reads only five explicitly named application members from the archive; tests and the test-login router are never installed.
2. Refuses unsupported/custom startup commands, missing/ambiguous dashboard hooks, symlinked installation paths, multiple/unidentified miner processes, unsafe board temperatures, incompatible libraries and invalid preferences.
3. Creates a private root-owned mode-0700 recovery directory under `/var/backups/bkb-cooling-*`. The durable manifest records file hashes and original ownership/modes. A private copy of miner.conf is retained for manual recovery, but is never restored over later operator changes automatically. Backups contain private pool configuration: never publish them.
4. Pauses cron, gracefully terminates only the verified miner PID and waits for it to exit. It does not force-kill the miner if graceful shutdown fails.
5. Atomically installs the verified miner, four web files and startup helper; minimally integrates the existing dashboard/startup script. Existing unrelated dashboard content and CRLF line endings are preserved. The old broad process-name search is replaced by `pgrep -x sgminer` so an installer/repository pathname containing `sgminer` cannot suppress startup.
6. Makes `/opt/scripta`, `/opt/scripta/startup` and `/opt/scripta/bin` root-owned mode 0755 to protect the newly installed root-executed startup/binary files from replacement. This may prevent legacy web-based self-update mechanisms from writing those directories. Existing directory ownership/modes are backed up and restored on rollback; this is not a comprehensive hardening of the legacy UI. The preference directory remains www-data-owned mode 0700 and its JSON mode 0600. The helper is installed under a root-controlled `/usr/local/libexec`.
7. Starts mining with conservative 100% fan duty, waits for fresh healthy fan acknowledgement and verifies API access **as www-data**, then runs the actual startup helper and confirms the selected preference is acknowledged. Checks that miner.conf did not change, then resumes cron.
8. On a recoverable installation/validation failure, attempts to restore all original application files and launch the original miner conservatively at 100%, then restores cron. Displaced/new files are retained inside the recovery backup. Recovery may fail if hardware, services or storage fail; always read the final result and verify mining rather than assuming a rollback succeeded.

A repeat installation is a no-op only when files, preference and required ownership/modes already match. The installer takes an exclusive installation lock and refreshes its plan before modifying files.

## Rollback

Use the **exact backup path printed by this installation**, not a guessed directory or an older unrelated backup. Stop using the webUI/configuration editors and schedule another maintenance window:

```sh
sudo python3 ./install-bkb-cooling.py --rollback /var/backups/bkb-cooling-EXACT-SUFFIX --confirm-bkb --allow-restart
```

Rollback validates the private manifest and every original-file checksum before restoring anything. It refuses automatic rollback if installed application files were subsequently edited; use the retained originals for a reviewed manual recovery instead. Changed cooling preferences are retained with displaced files. Original directory permissions are restored, and newly created directories are left in place rather than recursively deleted. Pool configuration is not rolled back. The original miner is launched at conservative 100% duty, not necessarily its previous runtime fan setting.

The explicit rollback critical section ignores terminal interrupt/hangup signals to avoid stranding it halfway through restoration. SIGKILL, power failure, storage failure and lost hardware communication cannot be made transactional; retain an independent way to access the controller and the printed backup path. If a failed install left an incomplete manifest, the automatic `--rollback` command refuses it: review the manifest and originals for manual recovery.

If the installer reports **CRITICAL: cron restoration failed**, check mining immediately and restore the watchdog with `sudo service cron start`. Do not blindly rerun the installer or force a reboot. A UI rollback does not undo a command already sent to hardware.

## Validation scope

Offline tests cover success, validation failure, partial write failure, graceful-stop failure, service-pause failure, interrupted stop, original restart, unchanged pool data, operator configuration edits, preference preservation, idempotence/permissions, custom hooks/startup rejection, corrupt/unknown backups, changed-file rollback refusal and watchdog restoration failures. Actual pinned payload hashes/ELF/archive members are verified locally.

Twenty installer tests passed, including an offline transaction/rollback using the actual pinned release binary and panel archive. The existing eight startup-helper tests and frontend tests also passed; Python 3.5 grammar compatibility was checked. No real service, API mutation or miner restart was used in these installer tests.

Run `python3 cooling-panel/tests/installer.py` from the repository. Set `BKB_RELEASE_ASSETS` to the extracted bundle directory to include the actual-asset test. Tests use a temporary filesystem and fake services/miner/API; they never restart a real miner. Live install/restart succeeded on 8 October. Live rollback and physical fault qualification remain untested.
