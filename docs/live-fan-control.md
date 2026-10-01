# Live fan-speed control

## Summary

[`0001-live-baikal-fan-control.patch`](../patches/0001-live-baikal-fan-control.patch)
adds live Baikal fan-speed control through sgminer's existing `ascset` API.

The patch:

- accepts an integer fan percentage from 0 through 100;
- sends the existing `BAIKAL_SET_OPTION` command to every detected logical
  miner on the selected physical controller;
- preserves each board's current clock and algorithm, plus the controller's
  existing cutoff temperature;
- updates the shared in-memory fan-speed state after all commands succeed; and
- reports invalid values and device-command failures through `ascset`.

## Compatibility

The patch applies to
[`cod3gen/sgminer-baikal`](https://github.com/cod3gen/sgminer-baikal) at commit
[`3cde8deca53f83ac65bc685b988166bd17930753`](https://github.com/cod3gen/sgminer-baikal/commit/3cde8deca53f83ac65bc685b988166bd17930753).

It modifies the USB Baikal driver in `driver-baikalu.c`.

## Apply

From a clean upstream checkout:

```sh
git checkout 3cde8deca53f83ac65bc685b988166bd17930753
git apply --check /path/to/0001-live-baikal-fan-control.patch
git apply /path/to/0001-live-baikal-fan-control.patch
```

Build and install sgminer using the upstream instructions. Installing the
patched binary requires one restart; subsequent fan changes do not restart
sgminer.

## Use

Set the fan to 30 percent, using the appropriate Baikal ASC number in place of
`0` when necessary:

```sh
printf '%s' '{"command":"ascset","parameter":"0,fan,30"}' \
  | nc 127.0.0.1 4028
```

The selected ASC identifies a logical miner on a physical controller. The
driver applies the new fan value to every detected logical miner that shares
that controller, so the result does not depend on which logical board owns the
physical fan connector.

Query the driver's supported runtime options with:

```sh
printf '%s' '{"command":"ascset","parameter":"0,help"}' \
  | nc 127.0.0.1 4028
```

Values below 0, above 100, or containing non-numeric trailing characters are
rejected without sending a device command.

## Implementation notes

`BAIKAL_SET_OPTION` carries the clock, algorithm, cutoff temperature, and fan
speed together. The setter therefore resends the complete option tuple for
each detected logical miner rather than changing only the fan byte in
isolation.

Logical miners created by the USB driver share one `baikal_info` structure.
The setter uses that shared state to limit the update to the selected physical
controller while retaining each logical miner's current clock and algorithm.

The in-memory `fanspeed` value is updated only after every matching logical
miner accepts the command. A device-command failure is returned through
`ascset`.

## Verification

The patch has been validated with:

```sh
git apply --check patches/0001-live-baikal-fan-control.patch
make sgminer-driver-baikalu.o
```

The modified `driver-baikalu.c` compiles successfully with the upstream build
system. Hardware validation is still required on a supported Baikal miner.
