# Baikal sgminer enhancements

A collection of focused, reviewable enhancements for
[`cod3gen/sgminer-baikal`](https://github.com/cod3gen/sgminer-baikal).

Enhancements are maintained as standalone patches so they can be reviewed,
tested, and adopted independently. Each patch has accompanying documentation
covering compatibility, behavior, installation, usage, and verification.

## Stable fan-control release

[v0.3.0 — Live fan control + webUI Cooling panel](https://github.com/Spectre-Works/baikal-sgminer-enhancements/releases/tag/v0.3.0) includes the fan-only ARM hard-float binary and complete corresponding source, Automatic/Manual cooling controls in Scripta, optional saved startup preferences, tests, documentation, and SHA-256 checksums. See the [release guide](docs/release-v0.3.0.md), [Cooling panel installation guide](docs/cooling-panel.md), and [fan-control API guide](docs/automatic-fan-control.md). The miner executable is unchanged from v0.2.0; this release adds the webUI integration and startup helper.

This release contains **no experimental live clock or overclock API**. The 480 MHz reported by some controllers is not proof of physical overclocking. Automatic mode remains runtime-only in the miner itself; the optional Cooling panel startup helper restores a saved preference. The curve monitors hash boards, not the host CPU, and fan telemetry is command acknowledgement rather than measured RPM. Actual production restart-persistence validation remains pending; simulated startup tests pass.

## Patch catalog

| Enhancement | Patch | Documentation |
| --- | --- | --- |
| Live fan-speed control | [`0001-live-baikal-fan-control.patch`](patches/0001-live-baikal-fan-control.patch) | [Live fan-speed control](docs/live-fan-control.md) |
| Automatic fan control (cumulative replacement for 0001) | [`0002-automatic-baikal-fan-control.patch`](patches/0002-automatic-baikal-fan-control.patch) | [Automatic fan control](docs/automatic-fan-control.md) |
| Scripta Cooling panel and startup preference helper | [`cooling-panel/`](cooling-panel/) | [Cooling panel](docs/cooling-panel.md) |

## Repository layout

- `patches/` contains numbered patches intended for clean upstream checkouts.
- `docs/` contains the detailed documentation for each enhancement.
- `cooling-panel/` contains the fan-only PHP/Angular integration, startup helper, integration patches and tests; it does not replace the stock dashboard wholesale.

## Applying patches

Compatibility and application instructions can vary by enhancement. Consult
the linked document in the patch catalog before applying a patch.

As a general workflow, start with a clean upstream checkout, select the base
revision documented for the patch, and run:

```sh
git apply --check /path/to/patch
git apply /path/to/patch
```

Build and validate the result using the upstream project's instructions and
the patch-specific verification notes.

## Contributing

Keep patches narrowly scoped and independently applicable. New enhancements
should include:

- a numbered patch in `patches/`;
- a focused document in `docs/`;
- a patch-catalog entry in this README;
- the exact compatible upstream revision; and
- reproducible validation steps and results.

## License

This repository and its patches are licensed under the GNU General Public
License v3.0. See [`LICENSE`](LICENSE).
