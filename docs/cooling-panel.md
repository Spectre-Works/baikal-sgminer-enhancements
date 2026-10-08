# Scripta Cooling panel — v0.3.0

One shared-fan card on Status controls the supported three-board BK-B controller. It requires the live/automatic fan API in the included fan-only miner release. It is not a generic dashboard for other Baikal models or multiple controllers.

## Controls and telemetry

- Apply now: Automatic or integer Manual duty 10–100%, running setting only.
- Save for restart: selected mode/manual duty, saved independently; no immediate change or mining restart.
- Full Cooling: Manual 100% now, without replacing the saved preference.
- Restore Automatic: enable the existing governor now, without replacing the saved preference.
- Clear recovered fault: allowed only after temperature telemetry and fan acknowledgement recover; never automatic.

Displays mode, requested and acknowledged duty, hottest board, last successful update, pending/fault/failsafe/unavailable state. A queued response is not displayed as acknowledgement. Browser polls preserve unsaved edits; browser closure does not stop the in-miner governor. Manual duty is restricted to 10–100% in this UI, although the raw API has a wider range. That minimum is not a guarantee of adequate airflow or spin-up for every fan.

The curve uses hottest hash-board temperature, **not Pi temperature**: below 40°C → 10%; 40–44°C → 25%; 45–47°C → 40%; 48–50°C → 65%; ≥51°C → 100%. Increases happen on the next worker pass; reductions take 60 continuous seconds at least 2°C below the current threshold, one step at a time. Invalid/missing/15-second-stale telemetry requests 100% in Automatic mode. USB failure can prevent delivery; acknowledged duty is not RPM or proof of fan rotation. Manual mode does not follow the curve. The existing thermal cutoff remains unchanged.

## Compatibility and security

Tested on existing BK-B Scripta with PHP 5.6, Python 2/3 startup runtime and its existing Angular/Bootstrap assets. No new browser framework or package installation is needed. PHP requires its existing OpenSSL support and localhost TCP API access. Verify `ascset` access as www-data without broadening network access. Compatible stats must include all `Fan ...` and temperature-validity/age fields described in the API guide. Controller identity is resolved from DEVS IDs/ASC and STATS IDs BKLU0–2, not array order; missing, ambiguous or disagreeing data is rejected.

The new endpoint enforces the existing logged-in session, fan-only actions, CSRF tokens on POST, strict integer validation, bounded input/API response sizes and API deadlines. It does not provide arbitrary commands, a shell proxy, or a web-callable privileged helper. Existing legacy HTTP/password handling and unrelated generic API routes are **not** hardened by this change. Keep Scripta on a trusted LAN; this release does not make it safe to expose to the internet.

## Installation

Use the release checksum manifest first. If installing/upgrading the miner executable, follow the separate binary guide and schedule an approved mining maintenance window. **Do not replace the running executable merely to install this panel.** The panel alone can be installed without a mining restart when the required fan API is already available.

1. Back up `/var/www/index.php`, `/var/www/partials/status.html` and, for optional persistence, `/opt/scripta/startup/miner-start.sh` to a uniquely named root-only directory outside the web root. Record hashes, ownership and modes. Preserve existing customizations and never publish miner.conf or backups containing pool credentials.
2. Stage/extract the Cooling panel asset outside `/var/www`. Inspect both integration patches. They target the inspected stock layout; if context differs, stop and adapt the small integrations manually rather than overwriting customized files. The web patch loads `ng/cooling.js` after `ng/controllers.js` and includes `partials/fan.html` before Devices. It leaves unrelated dashboard features intact.
3. Copy only the four new web files from `cooling-panel/package/web/` into their corresponding `/var/www/` subdirectories: `f_fan.php`, `inc/fan.inc.php`, `ng/cooling.js`, `partials/fan.html`. Use readable, non-executable PHP/JS/HTML file permissions (0644), with administrator-controlled ownership. Never install `tests/`, preview files or the test router in the public web root.
4. After backups, normalize CRLF line endings if necessary without removing other content. Check and apply the integration patch, using the actual absolute staging path:

```sh
sed -i 's/\r$//' /var/www/index.php /var/www/partials/status.html
patch --dry-run -d /var/www -p1 < /absolute/staging/cooling-panel/scripta-webui.patch
patch -d /var/www -p1 < /absolute/staging/cooling-panel/scripta-webui.patch
php -l /var/www/f_fan.php
php -l /var/www/inc/fan.inc.php
php -l /var/www/index.php
```

5. Create `/opt/scripta/etc/cooling` owned by www-data, mode 0700, even if startup restoration is not yet installed. The panel writes versioned JSON there with mode 0600. Use Save for restart only once the helper below is installed; saving does not itself schedule restoration.
6. Optional persistence: install `bkb-cooling-startup.py` at `/usr/local/libexec/bkb-cooling-startup.py`, root:root 0755, under a root-controlled directory. Inspect, dry-run and apply `scripta-startup.patch` from `/opt/scripta/startup` with `-p1`. Keep the startup script administrator-controlled and non-web-writable; legacy parent-directory permissions also matter. Do not add new cron entries if the existing Scripta startup watchdog already invokes this script. Verify shell/Python syntax without executing the startup script or restarting mining:

```sh
bash -n /opt/scripta/startup/miner-start.sh
python -m py_compile /usr/local/libexec/bkb-cooling-startup.py
```

The patched startup script launches the existing miner conservatively with `--baikal-fan 100`. The helper waits for healthy acknowledged telemetry, applies a saved preference once per miner PID/start-time identity and checks acknowledgement. No preference leaves Manual 100% at startup. Uncertainty permits only a best-effort 100% request, never repeated lower-duty writes. It never clears faults, restarts mining or continuously overwrites operator changes. A corrupt preference is not executed as code. Runtime guards are stored in root-owned `/run`; outcomes log as `BK-B cooling startup` in syslog/journald.

7. Hard-refresh Status, verify read-only data against the miner API, then supervise Full Cooling and Restore Automatic acknowledgements. Save Automatic if wanted and confirm JSON/permissions. Check logs and continued accepted shares/hardware-error counts. Actual restart/reboot persistence must be tested in a separately approved maintenance window; it was not tested on production during this release's live validation.

Preference schema: `{"version":1,"mode":"auto","duty":25}` or mode manual with duty 10–100. The duty is retained for manual preference even in automatic mode. Live commands do not save; saving does not apply. Fan changes rely on the existing fan driver's preservation of board clock/algorithm/cutoff state. No clock controls are exposed.

## Rollback

Restore the exact backed-up index.php/status.html/startup script with recorded ownership/modes. Move the five new application files and preference directory into the recovery backup rather than deleting them. Do not replace binaries or flash firmware for a panel rollback. Restoring files does not undo an already-applied fan command: restore a safe running mode separately if needed. Do not restart mining without approval.

## Tests and validation limits

From `cooling-panel/`: `node tests/frontend.js`, `python3 tests/startup.py`, and `php tests/backend.php`. The PHP fixture suite writes preferences only inside its own temporary directory. `tests/http_checks.py` runs an isolated localhost PHP server/session directory against an already-running compatible miner API, and deliberately sends only rejected mutations; do not expose its router. Run PHP syntax checks and JavaScript syntax checks too.

Live panel validation: actual login/dashboard rendering; Full Cooling acknowledged 100%; Restore Automatic acknowledged with normal 100→65→40→25% steps; saving/reloading Automatic; HTTP auth/CSRF/validation/method/size rejection; unchanged miner process/binary/configuration and clock-selector/algorithm/cutoff fields; continuing shares with no hardware errors/rejects during the observation. Operator subsequently reported successful use. The live host binary was not the newly packaged fan-only binary; the protocol-compatible panel was validated against the existing host build. The packaged miner remains the previously tested fan-only v0.2.0 artifact.

Simulated tests cover startup acknowledgement, lost replies/full-cooling fallback, once-per-process behavior, invalid preferences, stale telemetry, backend guards and frontend lifecycle. Actual production restart persistence, induced overheat/USB loss/fan disconnection and latched-fault clearing were not tested live. There is no physical RPM/airflow measurement or claim of long-term thermal qualification.
