# WebUI modification identification (v0.3.2)

The Cooling panel footer identifies the installed modification as **Baikal
sgminer enhancements**, displays its version and describes the scope as **Live
fan control + Cooling panel**. It explicitly says **Modified software** and links
to the project's GitHub repository for source, releases and documentation.

The label is part of `cooling-panel/package/web/partials/fan.html`. It is static,
so it remains visible when miner telemetry is unavailable. GitHub is a normal
outbound link, not an embedded resource or update check; loading the miner's page
does not fetch anything from GitHub. The link opens in a separate tab with
`noopener noreferrer`.

This version identifies the enhancement/UI package, not the board firmware,
the upstream sgminer version string or a measured clock frequency. The
`v0.3.2` label identifies this release's UI package. Update the version in both
the template and frontend test when preparing future releases; do not relabel
previously published archives.

This change does not alter fan policy, clock behavior, pool configuration,
startup settings or API permissions. The v0.3.2 installer pins the updated
v0.3.2 panel archive and the unchanged v0.3.0 fan-only miner. Its bundle includes
both payloads, complete corresponding miner source, licenses and checksums.

Run `node cooling-panel/tests/frontend.js` to check the identity/link and the
existing controller behavior.
