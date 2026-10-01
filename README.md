# Baikal sgminer enhancements

A collection of focused, reviewable enhancements for
[`cod3gen/sgminer-baikal`](https://github.com/cod3gen/sgminer-baikal).

Enhancements are maintained as standalone patches so they can be reviewed,
tested, and adopted independently. Each patch has accompanying documentation
covering compatibility, behavior, installation, usage, and verification.

## Patch catalog

| Enhancement | Patch | Documentation |
| --- | --- | --- |
| Live fan-speed control | [`0001-live-baikal-fan-control.patch`](patches/0001-live-baikal-fan-control.patch) | [Live fan-speed control](docs/live-fan-control.md) |

## Repository layout

- `patches/` contains numbered patches intended for clean upstream checkouts.
- `docs/` contains the detailed documentation for each enhancement.

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
