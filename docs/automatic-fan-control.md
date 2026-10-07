# Automatic Baikal fan control — implementation and review notes

Release: v0.2.0 — 2026-10-07

Based on cod3gen/sgminer-baikal commit `3cde8deca53f83ac65bc685b988166bd17930753`. The fan controller has been used and tested on a live BK-B. See [release installation and build instructions](release-v0.2.0.md) for the source archive and matching ARM build. Experimental clock-control code is not part of this release.

## Behavior

The hottest logical hash board on a USB controller determines the fan target:

| Temperature | Fan duty |
| --- | ---: |
| Below 40°C | 10% |
| 40–44°C | 25% |
| 45–47°C | 40% |
| 48–50°C | 65% |
| 51°C and above | 100% |

The governor checks once per second. Increases take effect at the next check. A reduction requires 60 continuous seconds at least 2°C below the current step's lower threshold, and reduces only one step at a time. For example, 25% falls to 10% only after remaining at or below 38°C for 60 seconds. A warm excursion restarts that timer.

Startup remains in manual mode using the configured startup fan duty (100% by default). Automatic mode is explicitly enabled through the API and is not persisted across restart.

Missing boards, zero or implausible temperatures, or samples aged 15 seconds or more force 100% in automatic mode. Recovery uses the same delayed downward steps. An option-command failure triggers a best-effort 100% broadcast and latches a USB fault. Fan reductions remain blocked until the operator clears that fault with fresh healthy telemetry and a fully acknowledged setting.

The existing 55°C cutoff and 40°C host recovery are retained. No runtime clock adjustment or overclock command is provided. Clock encoding and model defaults are unchanged.

## Preserving clock and algorithm

The driver records each board's exact clock-selector byte, algorithm mode, and cutoff when its startup option command succeeds. A fan update resends those bytes and changes only the fan field.

Reported MHz remains separate. Thus a board that reports 480 MHz after a startup request encoded from 400 MHz continues receiving its original selector (2) during fan updates. It is not re-encoded as selector 10.

Algorithm state follows the successfully sent work's base algorithm mode under the same USB mutex. SEND_WORK's optional midstate variant is not substituted into the SET_OPTION algorithm field.

A fan change is sent to every registered board ID on the selected physical controller. The driver completes the broadcast even after one board fails, then attempts 100% on every available board. It never reports a partial broadcast as fully acknowledged.

## Scheduling and locking

A small joinable controller worker calls the governor once per second. All state changes and complete broadcasts use the controller's existing USB mutex, so mining commands and algorithm updates cannot interleave with a fan broadcast.

The worker is started by logical miner 0's initialization and joined at its shutdown. Cleanup attempts the 100% fallback before stopping the worker. Waiting for new pool work now releases the USB mutex, allowing stale telemetry to trigger the fallback during a pool outage.

The 15-second threshold is evaluated on the next worker pass; actual application also depends on USB transfer latency. Complete USB loss prevents software from guaranteeing any physical fan setting. The logs and API distinguish acknowledged duty from unknown state. Existing firmware cutoff remains the hardware protection in that situation.

## API

The generic sgminer API is unchanged. Run these commands on the miner after installing a compatible build:

```sh
# Enable automatic mode.
printf '%s' '{"command":"ascset","parameter":"0,fan-auto,on"}' | nc -w 2 127.0.0.1 4028

# Disable automatic mode and retain the last acknowledged duty.
printf '%s' '{"command":"ascset","parameter":"0,fan-auto,off"}' | nc -w 2 127.0.0.1 4028

# Set a manual duty; this disables automatic mode.
printf '%s' '{"command":"ascset","parameter":"0,fan,25"}' | nc -w 2 127.0.0.1 4028

# Clear a latched USB fault after recovery.
printf '%s' '{"command":"ascset","parameter":"0,fan-reset,yes"}' | nc -w 2 127.0.0.1 4028

# Inspect acknowledgement and failsafe state.
printf '%s' '{"command":"stats"}' | nc -w 2 127.0.0.1 4028
```

Any logical ASC on the same controller selects the same fan governor. Values outside 0–100, fractional values, and trailing nonnumeric characters are rejected.

API setters queue requests for the worker. An `ascset` success means the request was accepted, not that the hardware has already acknowledged it. This differs from the original synchronous manual-fan patch. Check `Fan Pending`, `Fan Acknowledged Valid`, and `Fan Fault` before relying on a setting.

Added stats fields:

- Fan Mode, Fan Requested, Fan Acknowledged;
- Fan Acknowledged Valid, Fan Pending, Fan Fault, Fan Telemetry Failsafe;
- Fan Hottest (−1 when telemetry is incomplete);
- Option Clock Selector, Option Algorithm Mode, Option Cutoff;
- Temperature Age (seconds), Temperature Valid.

FWV/HWV now use their correct one-byte types instead of reading adjacent memory through an `int *` cast. Commanded duty is not RPM telemetry; this implementation does not query a fan tachometer.

## Safety and compatibility limits

Only hash-board temperatures are inputs to the curve; the host CPU temperature is not monitored. The 10% minimum worked on the tested running fan, but cold-start spin-up and compatibility with replacement fans are not certified. Qualify those before unattended use. This release does not certify firmware thermal protection or eliminate the need for supervision during initial deployment.

The displayed 480 MHz seen on the tested BK-B is decoded from a controller response byte of 240. It is not a clock setting introduced by this patch and does not prove physical overclocking. Fan updates preserve the requested raw selector rather than the displayed MHz. The ARM release has the model-specific 400 MHz startup request; that is a software request, not a measured physical frequency.

Bind the miner API to localhost or a trusted management network. Writable API access permits fan changes; do not expose it to the public Internet. Existing upstream API authorization settings remain unchanged.

## Patch packaging

`0002-automatic-baikal-fan-control.patch` is cumulative and replaces `0001-live-baikal-fan-control.patch`. Apply it to a clean upstream checkout at the commit above; do not stack both patches.

For a local source checkout already carrying 0001, reverse that patch first, preserve any model-specific default-clock edits, then apply 0002. Do not use these source instructions to modify the running miner before deployment approval.

```sh
git apply --check /path/to/0002-automatic-baikal-fan-control.patch
git apply /path/to/0002-automatic-baikal-fan-control.patch
```

Files changed: `driver-baikalu.c`, `driver-baikal.h`, `Makefile.am`, new `baikal-fan-policy.h`, and offline tests under `tests/`.

The patch intentionally leaves `BAIKAL_CLK_DEF` untouched. The live BK-B's existing build uses 400 MHz; retain that local model-specific build value when preparing an ARM binary.

## Verification performed

Passed:

- Patch application check against the exact upstream Git index.
- Reverse-application check against the implementation checkout.
- Compilation of `sgminer-driver-baikalu.o`.
- Mocked USB tests exercising the actual driver functions, including capturing the startup tuple, preserving it despite a different reported clock, broadcasting to all three IDs, partial failure, missing board, wrong-ID/wrong-command replies, zero-length replies, and short writes.
- Curve-boundary, immediate-increase, continuous-hysteresis, interrupted-hold, and one-step-decrease tests.
- API validation and deferred-application tests.
- Stale and invalid telemetry, fault reset, and fault-latch tests.
- Worker test proving stale fallback occurs without further mining-result polls.
- AddressSanitizer and UndefinedBehaviorSanitizer tests; leak detection disabled because this environment's process tracing prevents LeakSanitizer from running.

Reproduce after configuring the upstream checkout:

```sh
sh tests/run-baikal-fan-tests.sh
TEST_CFLAGS='-fsanitize=address,undefined --param asan-globals=0' \
  ASAN_OPTIONS=detect_leaks=0 sh tests/run-baikal-fan-tests.sh
make sgminer-driver-baikalu.o
```

The full ARM executable is built natively on the BK-B controller for this release, and the mock-USB tests run on that controller. Previous modern-x86 full-build attempts hit legacy upstream compiler and USB-library issues; those unrelated issues are not included in the patch.

The fan logic has been exercised on a live three-board BK-B, including acknowledged fan settings and automatic fan operation. The operator reported successful operation and testing. Fault injection remains an offline/mock test, not a deliberate live USB or fan disconnection. The newly packaged release binary is checked for ARM format, version output, dependency resolution, and absence of experimental clock commands; it is not installed during release packaging. No measured fan-RPM or independent physical-duty readback is available.

## Deployment review checklist

1. Build with the existing ARM toolchain and retain the BK-B's 400 MHz default.
2. Preserve the installed binary and configuration with checksums.
3. Start at manual 100%, verify all three boards and unchanged option selectors/modes/cutoff.
4. Verify acknowledged manual duties before enabling automatic mode.
5. Confirm that 10% reliably starts the fan after a cold start, not just keeps an already spinning fan running.
6. Enable automatic mode during a supervised soak; inspect the hottest board, upward transitions, downward holds, and telemetry age.
7. Test simulated failures in the mock harness, rather than unplugging boards or disconnecting the fan on a running miner.
8. Confirm successful worker shutdown and conservative manual mode after restart.

Back up the working binary and configuration before any installation. Follow the release guide and validate the device before leaving it unattended.
