# RKR keyboard test platform — v1

One keyboard application for the small, two-cable prototype. Includes replacement Arduino firmware, editable motion settings, explicit simulation, session logs, tests, and unchanged original scripts in `legacy/`.

**Read this file first.** The included motions and ±560-pulse limits are starting examples, not measured safe travel limits for your robot. The ±560 range comes from an uploaded sketch. Validate smaller travel with unloaded/disconnected cables before testing the assembled robot.

## What this version does

- Independent bidirectional control of both motors, including simultaneous key presses.
- Coupled left/right motion with release-to-tighten ratio `A`.
- Fixed-endpoint left and right curl actions; pressing again does not add another curl.
- Three editable sequences with absolute waypoints, speed, repetitions and dwell.
- Live per-motor signed step-pulse counts and calculated motor revolutions.
- CSV recording of acknowledged positions and commands, with the session's configuration saved alongside.
- Host and firmware travel checks, explicit reference and arming, stop on key release, focus-loss disarming, and a 500 ms firmware communication watchdog.

This release has **no camera, gesture recognition, encoder, force sensor, or current sensor**. It uses constant-rate motion without acceleration/deceleration ramps. Keep speeds low until tested. Abrupt starts, stops or reversals can cause missed steps under load. A future trajectory version should add coordinated acceleration in the firmware, not just delays in Python.

## Folder map

| File | Purpose |
|---|---|
| `keyboard_control.py` | Run this: keyboard window and display |
| `config.json` | Change motion parameters here |
| `controller.py` | One motion owner, sequence execution, stop/arm/reference rules |
| `motion.py` | Logical directions, ratio, motion planning and validation |
| `transport.py` | Serial protocol and hardware-free simulator |
| `firmware/rkr_controller/rkr_controller.ino` | Upload this replacement firmware |
| `SENSING_AND_ROADMAP.md` | Current/tension sensing and subsequent test versions |
| `tests/` | Python behavior tests and native firmware harness |
| `legacy/` | Six uploaded originals, preserved without changes |

Run terminal commands below from the extracted `rkr_keyboard_v1` directory. Use Python 3.10 or newer. `python` may be `python3` on Linux.

## First run: simulation

Tkinter is part of many Python desktop installations. On Linux Mint, install `python3-tk` if `import tkinter` fails. Simulation has no additional Python package requirements.

```bash
python keyboard_control.py --sim
```

Keep the window focused. Press **Z**, confirm reference zero, then **Enter** to arm. Try holding R/E/M/N or the arrows. Press J/L and 1/2/3 to test actions. Space cancels; Escape disarms; Q exits.

Simulation uses pulse-count timing and limits. It cannot predict robot shape, cable slack, load, electrical current or missed steps. A hardware connection error never silently switches to simulation.

## Hardware setup

Install the serial dependency in your preferred Python environment:

```bash
python -m pip install -r requirements.txt
```

Open `firmware/rkr_controller/rkr_controller.ino` in Arduino IDE, select the actual board and serial port, compile and upload. There are no external Arduino library dependencies. The supplied originals used AccelStepper; the new sketch uses its own coordinated pulse scheduler.

The wiring follows both uploaded Arduino sketches:

| Signal | Motor 1 | Motor 2 |
|---|---:|---:|
| STEP | D2 | D5 |
| DIR | D3 | D6 |
| ENABLE | D4 | D7 |

Baud rate: **115200**. Enable is assumed active LOW, matching the uploaded code. Confirm your actual driver module's input polarity and wiring; change `ENABLE_ACTIVE` in the sketch if required. NEMA 17 describes the motor frame, not its voltage/current rating or the driver module. The code alone cannot identify the exact installed driver.

Close Arduino Serial Monitor before running Python. List available ports:

```bash
python -m serial.tools.list_ports
```

Windows example:

```bash
python keyboard_control.py --port COM3
```

Linux example:

```bash
python3 keyboard_control.py --port /dev/ttyUSB0
```

Use the actual listed port, which might be `/dev/ttyACM0`. On Linux, a permission error usually requires serial-device group access (commonly `dialout`) and a fresh login. The keyboard UI uses Tk events; it does not need root privileges or the global `keyboard` package.

The application verifies `RKR 1`. Old firmware is incompatible and is refused. Opening a serial port can reset the Arduino. Every new application session requires reference zero again; do not reuse old recorded positions as if they were measured present positions.

## Establish the reference and verify directions

Start with cable load removed or suitably supported. Establish a known neutral physical configuration, with the cables gently tensioned. Do not force a powered motor shaft to position it. If the mechanism is moved while power is removed, counters are no longer a valid reference.

Press **Z while disarmed** to declare the current physical pose `[0, 0]`. This is a manual reference operation, not homing. Then press **Enter** to arm. Briefly tap R: motor 1 should tighten. Tap M: motor 2 should tighten. E and N should release their respective cables.

If one direction is wrong, quit and change that motor's `motor_signs` entry from `1` to `-1`, restart and re-establish the reference. If the left/right mapping is physically reversed, swap the motor assignments/wiring with power off or change the logical mapping deliberately. Logical motor 1 is the left cable and motor 2 the right cable.

If necessary, use small jogs to reach the neutral pose, press Escape, and set Z again. Only zero at an intentionally established physical reference: zeroing at an arbitrary curl makes the configured endpoints and limits refer to the wrong pose.

## Keyboard instructions

| Key | Behavior |
|---|---|
| Hold R / E | Motor 1 tighten / release |
| Hold M / N | Motor 2 tighten / release |
| Hold Left / Right | Coupled swing left / right |
| J / L | Move to left / right curl endpoint, then stop |
| 1 | Side-to-side sweep |
| 2 | Left curl and return |
| 3 | Custom two-cable sequence |
| H | Move to stored reference `[0, 0]`; no physical homing sensor |
| Space | Stop both motors immediately and discard the sequence |
| Escape | Stop and disarm |
| Enter | Arm after reference is set |
| Z | Confirm and set both counters to zero, only while disarmed |
| Q | Stop, disarm and quit |

Independent motor keys can be combined: R+N tightens motor 1 while releasing motor 2. Opposite keys on one motor cancel. Arrow keys take priority over independent keys; opposite arrows cancel each other. One-shot actions ignore keyboard autorepeat. A manual key interrupts a sequence. A new action cancels the previous action.

After Space/Escape, release all held keys before issuing new commands. Focus loss disarms and cancels motion; click the window and press Enter to resume. Manual key-release handling includes a short 35 ms debounce for Linux key repeat; it is not a hard real-time stop. Firmware stops pulses without a deceleration ramp. Holding torque remains enabled at stop/disarm and after the watchdog; disarm is not electrical power isolation.

## Customization

Edit `config.json` while the program is closed, then restart. JSON cannot contain comments or trailing commas. Keep an original copy and save experiment configurations under new names:

```bash
python keyboard_control.py --port COM3 --config experiment_02.json
```

| Setting | Units / interpretation | Default |
|---|---|---|
| `motor_signs` | Logical tightening mapped to electrical direction; each ±1 | `[1,1]` |
| `steps_per_revolution` | Driver STEP pulses per motor-shaft revolution | `[1600,1600]` |
| `limits` | Per-motor absolute minimum/maximum logical pulse counts | `[[-560,560],[-560,560]]` |
| `jog_speed` | Tightening/independent motor pulse rate | 150 pulses/s |
| `jog_segment_steps` | Leader displacement in each short manual segment | 15 pulses |
| `A` | Releasing speed divided by tightening speed, manual arrows only | 0.25 |
| `curl_speed` | Pulse rate of the faster motor during a curl or H return | 100 pulses/s |
| `curl_left_target` | Absolute `[motor1,motor2]` endpoint from reference | `[200,-50]` |
| `curl_right_target` | Absolute `[motor1,motor2]` endpoint from reference | `[-50,200]` |
| `preset_speed` | Faster motor's pulse rate during preset segments | 100 pulses/s |

Software accepts A from 0 to 2 and rates up to 1000 pulses/s. For A greater than 1, the releasing motor is faster; `jog_speed × A` must not exceed 1000. These are implementation bounds, not verified mechanical capabilities. Large jog segments reduce continuity overhead but can stop farther from a software boundary because the whole segment is rejected if either target would exceed its limit. The pair is never independently clipped, which would distort the coupling.

The firmware permits configured limits only within ±20000 pulses. Increase firmware bounds only after reviewing integer arithmetic, mechanical travel and test results. Settings validation rejects invalid values and out-of-range preset/curl targets before a session starts.

### Calibrating A

For a left swing:

`v1 = +v`, `v2 = -A·v`.

For a right swing:

`v1 = -A·v`, `v2 = +v`.

At A=0.25 and v=150 pulses/s, the nominal rates are +150 and -37.5 pulses/s. Short segments retain fractional pulse remainders, so small A values do not round away over repeated full segments. Discrete pulses, aborted segments and communication gaps mean instantaneous rates are not perfectly continuous.

Start with small movements near neutral. Observe the releasing cable. If it goes slack, try reducing A; if it remains overly tensioned, try increasing A while checking the tightening cable too. Change one quantity at a time and record the outcome. A single constant may work only over part of the curl: geometry, changing spool radius, compliance and friction can make the required ratio pose-dependent. A does not guarantee slack prevention.

A is a ratio of **pulse rates**, not automatically cable speeds. If pulley radii, microstepping or gearing differ, account for their different millimetres per pulse. Manual arrows use A; curl endpoints and preset waypoints are explicit independent settings and are **not automatically recalculated** when A changes.

### Calibrating curl stops

Jog gradually from reference while recording the two displayed counters. Stop before excessive tension or contact. Copy that pair into the appropriate curl target, quit/restart and re-establish reference. Validate from a nearby pose before attempting the whole motion from neutral.

Example: `[240,-60]` means motor 1 has wound 240 pulses and motor 2 has released 60 pulses relative to zero. Pressing J moves to that endpoint; pressing J again at the endpoint makes no additional movement. It does not mean “move 240 more pulses each time.” From the opposite curl, it moves directly along a straight path in the two-motor position coordinates. Validate that intermediate path too; legal endpoints alone do not guarantee a safe cable-tension path.

Without sensors, “fully curled” is an experimentally chosen endpoint. The system does not detect the actual fully-curled shape. A stall is not a valid homing method: emitted pulses can continue while the shaft is stationary, invalidating the position estimate.

### Programming the three actions

Each of `presets.1`, `presets.2`, and `presets.3` has:

```json
{
  "name": "Side-to-side sweep",
  "repeat": 2,
  "dwell_ms": 300,
  "waypoints": [[100, -25], [-25, 100], [0, 0]]
}
```

Each waypoint is an absolute position pair. Both axes traverse their displacement in a coordinated segment: the faster axis uses `preset_speed`; the other is proportionally slower. The controller waits for the firmware to report completion, then dwells, then advances. Repetition is finite. Space, Escape or focus loss cancels all remaining waypoints.

To reduce range, change all nonzero coordinates consistently, e.g. `[100,-25]` → `[40,-10]`. The first target is approached from the current pose; the program does not jump back to zero first. To require a return through reference, insert `[0,0]` as a waypoint. Returning to the same coordinates does not guarantee the same shape if there is backlash or slip.

Rename actions in the settings and document their physical intent for teammates. To remap keys, edit `MANUAL` and key dispatch in `keyboard_control.py`, `manual_vector()` and `action()` in `motion.py`, and the displayed key instructions together.

## Position accounting and logs

The Arduino increments each signed position count when it emits a STEP pulse. Python displays the acknowledged counts, not a time-based guess or the sum of requested travel. There are short telemetry delays: the display is sampled roughly every 50 ms. Acknowledgements and sample rows are written into `logs/` by default. Set `--log-dir PATH` to choose another location.

Motor revolutions = pulse count / pulses per motor revolution.

For a 1.8° motor at 1/8 microstepping, the example is 200 × 8 = 1600 pulses/revolution. **1600 is an unverified placeholder: set this from your actual motor and driver switches.** A 0.9° motor has 400 full steps/revolution. For geared spools, also account for the gear ratio when converting shaft rotation to spool rotation. Cable displacement additionally depends on effective winding radius; it is not displayed as if known.

Counters reset on Arduino reset or confirmed Z. Reference changes appear as ZERO rows in the CSV. Power loss, manual movement, driver disable, missed steps, loose couplings or spool slip break the relationship between counters and physical position. Re-reference after these events. No EEPROM persistence or automatic recovery is attempted.

Logs are local to the computer running the app. They record configuration and commands/telemetry, not individual pulse timestamps, motor torque or actual robot pose. Connection errors are displayed and lock further motion until restart. Logs may end at the last acknowledged sample after a disconnect; the firmware may have emitted additional pulses before watchdog stop.

## Protocol reference

Line-oriented ASCII, newline-terminated, 115200 baud. One command outstanding at a time. Firmware does not accept legacy MOVE1/SPEED1 commands.

| Command | Meaning |
|---|---|
| `HELLO` | Replies `RKR 1` |
| `DISARM` | Stop and inhibit further motion commands; retain holding torque |
| `INIT s1 s2 min1 max1 min2 max2` | Set direction signs and limits while stopped/disarmed; invalidate reference |
| `ZERO` | Set both counters to zero while stopped/disarmed/configured |
| `ARM` | Permit movement once referenced |
| `MOVE p1 p2 rate` | Coordinated absolute move; rate of faster axis in pulses/s |
| `STOP` | Immediately cease pulses and discard current target; remain armed |
| `STATE` | Query status and refresh heartbeat |

Successful commands except HELLO reply `STATE p1 p2 busy armed referenced`. Errors reply `ERR reason`. `STATE`, accepted MOVE, ARM and STOP refresh contact timing. If communication stops for >500 ms while armed, firmware stops and disarms. STATE traffic after that does not automatically re-arm. Malformed, extra or fractional numeric arguments are rejected. An overlong input line is discarded through its newline, stops motion and disarms.

## Validation and known limits

Automated Python tests cover motion directions, A fractional accounting, absolute curls, stop/cancel, dwell, limits, invalid settings, sequence completion and watchdog behavior. A C++ harness executes the actual sketch against stubbed Arduino time/GPIO/serial and checks pulse counts, command parsing, stop, limits and watchdog behavior.

Run from this directory:

```bash
python -m unittest discover -s tests -v
```

Optional native firmware harness (requires a C++ compiler):

```bash
g++ -std=c++11 -Wall -Wextra -Werror -I tests/native tests/native/test_firmware.cpp -o firmware_test
./firmware_test
```

The native harness is **not an Arduino board compilation or physical hardware test**. This delivery has not been flashed onto your board, and GUI rendering and key behavior have not been verified on your desktop. Board selection, driver timing/polarity, attainable speed, mechanical travel, cable tension and stop latency need bench validation. Check Space, key release, focus loss and USB disconnection with an unloaded mechanism first. Keep an accessible hardware power stop; a PC keyboard is not a safety-rated emergency stop.

## Notes on the uploaded originals

- `step.ino`: independent AccelStepper commands, no position telemetry or travel limits.
- `arudino_rkr.ino`: adds checks at current ±560 positions, but accepts targets beyond those bounds; includes serial debug output.
- `dugmici.py`: independent and coupled keyboard chunks with hard-coded quarter-rate release.
- `dugmicitest.py`: adds arrow motion that remains latched until stopped.
- `samo_dugmici.py`: despite the filename, contains camera/MediaPipe gesture control; can call `arduino.readline()` when connection initialization failed.
- `u_oba_smera.py`: several commented experiments plus active thumb-direction gesture code and coupled release.

Some originals discard unread serial responses, send fractional values to integer command parsers, or leave motion continuing when a hand/camera is lost. They are preserved as source history, not alternative launchers for the new firmware.
