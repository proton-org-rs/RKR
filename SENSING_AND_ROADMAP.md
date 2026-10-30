# Sensing and systematic next versions

## Can a NEMA 17 report current spikes?

NEMA 17 is a mechanical frame designation. An ordinary four-wire stepper has no built-in current telemetry or shaft-position feedback. Current can be measured with additional electronics, but the motor itself cannot report it through STEP/DIR.

The uploaded Arduino code labels its drivers TB6600. Verify the actual module before choosing a circuit. Typical current-regulated stepper drivers chop their winding current to a set value. Increased mechanical load or a stall therefore does not necessarily create the obvious current rise familiar from an unregulated brushed DC motor. Current alone should not be assumed to identify “fully curled.”

There are distinct measurements:

| Measurement | What it can help with | Limitation |
|---|---|---|
| Per-driver supply current | Electrical logging and anomalies | Not winding current or a direct tension measurement; depends on speed and driver behavior |
| Motor phase current | Driver/winding behavior | Chopped bidirectional waveform; requires appropriate sensing, bandwidth and isolation/common-mode handling |
| Motor or spool encoder | Actual rotation, slip or missed-step detection depending on placement | Does not directly measure cable force or curl shape |
| Load cell per cable / tension-sensing idler | Slack and excessive cable force | Requires mechanical design and calibration; idler reaction is geometry-dependent |
| Driver-supported sensorless load/stall estimation | Possible additional stall signal | Requires a compatible driver, speed range and tuning; not a universal end-position detector |

For this prototype, prioritize two tension channels if the immediate goal is avoiding loose cables and stopping an over-tight curl. A load cell and suitable ADC/amplifier are one candidate approach; choose force range, mechanical arrangement and sample/update rate from the actual cable load and speed. A spring-loaded idler with displacement sensing is another possible approach. Neither is implemented or validated in v1.

Current sensing is still useful for experiments. To design that addition, record the exact driver module/model or photos, supply voltage, motor rated phase current, driver current setting, microstep setting and Arduino board. Decide whether you want one sensor per driver supply or actual phase measurements. Do not connect a motor phase or supply rail directly to an Arduino analog input.

## How to add sensing without restructuring everything

Retain logical motor positions and the shared Controller interface. Add sensor acquisition in firmware and include timestamped measurements in a versioned protocol. Do not invent a current value from pulse rate.

Log first with protection thresholds disabled on an unloaded/controlled rig. Compare normal movement, holds, reversals, different curl positions and carefully controlled load variations. Establish whether the signal reliably distinguishes the condition of interest. Sampling must capture the relevant dynamics; a slow display/logging rate is not a substitute for fast local protection.

Then implement a firmware-latched sensor fault: cancel both axes, prevent automatic restart, report the reason, and require an intentional reset. Consider filtering, persistence duration, plausible signal bounds, sensor disconnects, stale samples and minimum/maximum tension. Keep calibrated position bounds and the communication watchdog as independent protections. Determine experimentally whether holding torque or disabling the driver is appropriate after a particular mechanical fault.

If an encoder is fitted, retain two separate fields: commanded/emitted pulse position and measured position. Never silently replace one with the other or imply that current estimates are encoder feedback.

## Suggested testing versions

| Version | Purpose | Deliverable / acceptance test |
|---|---|---|
| v1 — keyboard baseline (included) | Verify wiring, signs, pulse scaling, A, limits and repeatable open-loop motions | Independent/coupled jogging, finite curls and three sequences; all stop paths checked |
| v2 — repeatable motion experiments | Improve trajectory quality and sweep A/speed/range reproducibly | Coordinated acceleration in firmware; experiment IDs; repeatability measurements; validated bounded sweeps |
| v3 — tension/current instrumentation | Measure slack, overload and electrical behavior | Firmware sampling, calibrated logs, validated fault handling and sensor-loss behavior |
| v4 — gesture input | Replace keyboard intent with hand-tracking intent | Same motion layer; hand/camera loss stops promptly; explicit activation, confidence filtering and one motion owner |

These are proposed future versions, not additional implemented scripts. Avoid copying the entire controller into separate experiments: keep one tested firmware/protocol, one motion layer, separate input frontends, and named settings files. The present `Controller.manual(keys)`, `start_action(key)` and `stop()` demonstrate that separation. A later gesture frontend can translate intent into that layer or a generalized vector API without directly issuing competing motor commands.

For each physical experiment record: prototype and spool revision, cable/preload setup, driver and microstepping, physical reference procedure, configuration filename, observed slack/tension, whether any steps were missed, and the resulting CSV. Change one parameter at a time during initial calibration.
