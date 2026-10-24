# WebUI and runtime identification (v0.3.4)

The Cooling panel footer displays **SPECTRE WORKS LLC**, identifies Baikal
sgminer enhancements and shows **Panel v0.3.4**. This static identity remains
visible when miner telemetry is unavailable. The adjacent **Running miner**
value comes from the running binary's `Enhancement Version` stats field through
`f_fan.php`; it is not inferred from the panel version or a saved preference.

Fresh compatible telemetry displays `v0.3.4`. Older binaries without that field
are labeled `Unidentified (legacy binary)`. A missing/stale panel response shows
`Unavailable`, rather than presenting a cached version as current. Both the
native `--version`/startup/TUI string and the API `version` response carry the
`-spectreworks-v0.3.4` suffix; the API also exposes `Enhancement Version: 0.3.4`.
The API protocol version and hardware/firmware versions keep their own identities.

The GitHub link remains a normal outbound link with `noopener noreferrer`.
Loading the panel does not query GitHub. Hard-refresh after deployment to load
the updated template. Never relabel previously published archives; VERSION and
the release consistency check govern new package versions. See AGENTS.md.

Run `node cooling-panel/tests/frontend.js`, the PHP backend tests and
`python3 tools/check-release-version.py` before release. Backend checks cover
legacy, invalid and current runtime identities. Live validation must also query
the actual running API and compare `/proc/PID/exe` with the released binary.
