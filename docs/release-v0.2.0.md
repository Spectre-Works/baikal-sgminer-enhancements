# v0.2.0 — BK-B automatic fan control

Released 7 October 2026. Based on cod3gen/sgminer-baikal commit `3cde8deca53f83ac65bc685b988166bd17930753`, plus the cumulative automatic-fan patch and a BK-B-specific 400 MHz startup default.

## Assets

- `sgminer-baikal-bkb-fan-v0.2.0-armhf`: fan-only ARM hard-float executable. Its upstream version string remains `5.6.2-BK_cod3gen_MOD`; identify this release by its asset name and checksum.
- `sgminer-baikal-bkb-fan-v0.2.0-source.tar.gz`: complete corresponding source, including bundled dependency sources/licenses, the fan-policy header, and mock-USB tests. The startup default is already set for BK-B.
- `0002-automatic-baikal-fan-control.patch`: cumulative source patch for clean upstream; replaces 0001, not an additional layer. It leaves model defaults untouched, so set the BK-B default separately when using the patch instead of the source archive.
- `automatic-fan-control.md`, `release-v0.2.0.md`, `BUILD-INFO.txt`, and `SHA256SUMS`.

Use the explicitly named source asset for the binary's corresponding source. GitHub's automatically generated source ZIP/tarball contains this enhancement/patch repository, not the full upstream miner tree.

## Compatibility

The binary is built natively on a BK-B's 32-bit ARMv7 controller running Ubuntu 16.04.2, using its existing GCC/toolchain and configuration. It is dynamically linked and intended for a matching stock-era environment, not a general ARM64, modern Raspberry Pi OS, or other Baikal-model binary. Check `BUILD-INFO.txt`, `file`, and `ldd` before installation; do not force incompatible libraries or install it on an unidentified model.

The requested startup clock is 400 MHz, cutoff 55°C, recovery 40°C, and default fan duty 100% unless existing configuration overrides it. There are no runtime clock-control commands. Reported MHz and estimated hashrate remain upstream behavior; neither establishes actual physical clock/overclock effectiveness.

## Installation and rollback

1. Download assets from the [v0.2.0 release](https://github.com/Spectre-Works/baikal-sgminer-enhancements/releases/tag/v0.2.0). In the download directory, verify `sha256sum -c SHA256SUMS`. Download every listed asset for a complete check, or check the relevant entries individually. Checksums verify asset consistency, not independent author identity.
2. Copy the executable to a staging location on the miner. Verify its checksum there, inspect `file` and `ldd`, and run only `--version` initially. Do not start a second miner against the live controller.
3. Make a uniquely named backup directory and preserve `/opt/scripta/bin/sgminer` and `/opt/scripta/etc/miner.conf`, recording their checksums. Preserve configuration file permissions; it may contain pool credentials. Do not publish the configuration.
4. With operator approval and supervision, stop the miner using its existing Scripta stop mechanism. On the tested installation, use `sudo bash /opt/scripta/startup/miner-stop.sh` and verify the miner stopped.
5. Install the staged binary as `/opt/scripta/bin/sgminer` with executable permissions. Run the existing start script as a **separate operation**: `sudo bash /opt/scripta/startup/miner-start.sh`. The legacy script's broad process-name search can be confused by a parent command containing `sgminer`.
6. Confirm all three boards, fresh temperatures, unchanged algorithm/cutoff, and valid fan acknowledgement. Initially use manual 100% duty. Then enable automatic mode with the command below and observe its transitions before unattended operation.

If startup or validation fails, stop the miner, restore the exact saved binary and permissions, and restart using the original mechanism. This release needs no firmware flashing, boot changes, or configuration migration. Enable automatic mode again after any restart if desired; runtime automatic mode is not persistent.

## API quick start

Run on the miner, respecting its existing API authorization configuration:

```sh
# Manual 100%; API success means queued, not applied.
printf '%s' '{"command":"ascset","parameter":"0,fan,100"}' | nc -w 2 127.0.0.1 4028

# Enable automatic mode explicitly after each restart.
printf '%s' '{"command":"ascset","parameter":"0,fan-auto,on"}' | nc -w 2 127.0.0.1 4028

# Query acknowledged duty, pending/fault state and hottest board.
printf '%s' '{"command":"stats"}' | nc -w 2 127.0.0.1 4028
```

Check `Fan Mode`, `Fan Requested`, `Fan Acknowledged`, `Fan Acknowledged Valid`, `Fan Pending`, `Fan Fault`, `Fan Telemetry Failsafe`, and `Fan Hottest`. These are not RPM measurements. See [full behavior/API documentation](automatic-fan-control.md) for manual/off/reset commands, curve thresholds and failure handling.

The hottest hash board selects 10/25/40/65/100% at thresholds 40/45/48/51°C. Increases occur on the next worker pass; reductions need a continuous 60-second hold with 2°C hysteresis. Invalid, missing or 15-second-stale board temperatures force 100% in automatic mode. USB loss can prevent that command from reaching the hardware. Host CPU temperature is not included. Qualify low-duty cold-start spin-up and replacement fans separately.

## Building from the source asset

Extract into a new directory; do not overlay a live checkout. On the matching existing ARM build environment:

```sh
tar -xzf sgminer-baikal-bkb-fan-v0.2.0-source.tar.gz
cd sgminer-baikal
autoreconf -fi
./configure
make -j1 CPPFLAGS=
sh tests/run-baikal-fan-tests.sh
./sgminer --version
```

Required tooling includes the legacy-compatible C compiler, make, autoconf/automake/libtool, and the curl/ncurses/udev development dependencies used by the existing configuration. Bundled Jansson and Baikal USB library sources are included. Existing Scripta files, pool configuration, or firmware are not part of the source archive. `BUILD-INFO.txt` records the native build environment and dependency checks.

The release build reuses the device's configured native build tree and unchanged cached objects/libraries, recompiling the changed header-dependent modules. The supplied source is the exact upstream source plus the fan patch and documented BK-B default. This is a corresponding-source release, not a claim of a bit-for-bit reproducible clean build. Modern compiler and platform incompatibilities in the legacy upstream project are not fixed here.

## Validation scope

The fan-only policy and actual driver/mock-USB tests pass locally and on the ARM controller. The same fan logic was used and tested on a live three-board BK-B. Native binary linking, version output and dependencies are checked; experimental clock-control symbols/messages are excluded. The newly packaged binary is not deployed as part of publishing this release. Overheat, USB-loss and fan-disconnection scenarios are not deliberately induced on live hardware; they are exercised in the mock harness.

## License

Miner modifications are GPL-3.0; upstream and dependency notices/licenses are retained in the source archive. The complete source accompanies the executable. Existing upstream licensing terms still apply; system libraries are not bundled in the release.
