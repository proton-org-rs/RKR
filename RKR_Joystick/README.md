# SpiRob Control Room · Joystick edition

Two workspaces control the same three-cable robot.

- **Operating** opens the joystick and motion buttons.
- **Testing** adds a parameter menu and pose calibration.

Both have a mouse joystick, keyboard support, return to reference, three single-cable curls, three two-cable curls, release all, dance, stop and disarm. Setup creates a separate desktop shortcut for each workspace.

## Start on Linux Mint

Extract the ZIP to a permanent folder. Open a terminal inside the extracted `RKR_Joystick` folder.

Install the system Python components if needed.

```bash
sudo apt install python3-venv python3-tk
```

Run setup once.

```bash
bash Setup_Linux.sh
```

Setup creates `.venv`, installs pySerial and places **SpiRob Operating** and **SpiRob Testing** shortcuts on the desktop and in the applications menu. If Mint asks, right-click the desktop icon and allow launching.

Use either shortcut. You can also run directly.

```bash
bash Start_Testing.sh
bash Start_Operating.sh
```

The shell launchers accept extra arguments.

```bash
bash Start_Testing.sh --sim
bash Start_Operating.sh --port /dev/ttyUSB0
```

If an environment is already installed, these commands are equivalent.

```bash
source .venv/bin/activate
python run_testing.py
python run_operating.py
```

The startup window lets you choose the port and switch on explicit simulation. `python app.py` offers both workspaces. Mode-specific shortcuts offer the corresponding workspace only.

To skip the startup screen, append `--direct`.

```bash
.venv/bin/python run_operating.py --direct --port /dev/ttyUSB0
```

If USB access is denied, add the current user to `dialout`, then log out and back in.

```bash
sudo usermod -aG dialout "$USER"
```

## Start on Windows

Install Python 3.10 or later with Tcl/Tk and the Python launcher. Extract the ZIP to a permanent folder, then double-click **Setup_Windows.cmd**.

Setup creates `.venv`, installs pySerial, and installs two desktop `.lnk` shortcuts with the supplied icon.

Open **SpiRob Operating** or **SpiRob Testing**. In the startup screen replace the Linux default port with the board's COM port, for example `COM3`.

The folder also contains **Start_Operating.cmd** and **Start_Testing.cmd**. To run with a visible terminal for diagnostics, use PowerShell.

```powershell
.\.venv\Scripts\python.exe run_testing.py --port COM3
```

List ports with the virtual environment's Python.

```powershell
.\.venv\Scripts\python.exe -m serial.tools.list_ports
```

On either OS, moving the folder breaks installed absolute shortcut paths. Run `install_shortcuts.py` again with that folder's virtual-environment Python after moving it. Existing shortcuts with the same names are replaced.

## Firmware compatibility

This package speaks the same **RKR3 1** protocol as the working three-cable firmware from this chat. An already working RKR3 1 controller can be used directly. The matching sketch is also included in `firmware/rkr_3cable/rkr_3cable.ino`.

Firmware targets Arduino Uno R3, classic ATmega328P Nano and Mega 2560. Use Arduino IDE to select the actual board and port, upload this sketch if needed, then close Serial Monitor.

| Cable | STEP | DIR | ENABLE |
|---|---|---|---|
| C1 | D2 | D3 | D4 |
| C2 | D5 | D6 | D7 |
| C3 | D8 | D9 | D10 |

Signal assignments and per-driver enable polarities are in the sketch. The provided firmware has active-LOW enables. Confirm these against the actual driver modules, particularly when mixing TB6600 modules and DRV8825 boards. Driver current limits and microstep settings are physical driver settings.

The firmware starts with its enable outputs inactive. Arm activates them. Stop, disarm and watchdog stops subsequently retain holding outputs. Power removal is a separate hardware action.

## Joystick behavior

Hold the left mouse button inside the circle and drag. Moving farther from the centre increases speed. Release the button to stop and hold the current pose. Moving outside the circle clamps the command to maximum magnitude.

The three labelled axis rays are separated by 120°.

- **C1** is at the top.
- **C2** is at the lower right.
- **C3** is at the lower left.

Toward C1, cable 1 takes up while cables 2 and 3 pay out. At the default equal multipliers their rates are in the proportion `+1, -0.5, -0.5`. The other two axes follow the same pattern.

Opposite C1, cables 2 and 3 take up while C1 pays out. Moving between these axes blends the three rates continuously. The centre dead zone commands zero velocity and leaves the robot at its current shape. **Return to reference** is a separate commanded movement.

The mixer projects the joystick vector onto each cable axis. The outer circle represents the configured maximum pulse speed. It is an empirical directional control for the three-cable geometry. Calibrate gains, axis orientation and cable assignments against the physical robot.

| Input | Action |
|---|---|
| Hold and drag left mouse button | Continuous direction and speed |
| Release mouse button | Hold current pose |
| Arrow keys or WASD | Steer at full joystick displacement, diagonals included |
| Hold 1, 2 or 3 | Move toward the corresponding cable |
| Shift + 1, 2 or 3 | Move away from that cable, using standard Latin/US key symbols |
| Enter | Arm with controls released |
| Home | Return to reference |
| Space or STOP | Cancel movement, hold current pose |
| Escape | Stop and disarm |
| Switch to another application | Stop and disarm |

Mouse and keyboard commands are spring-return controls. Manual input interrupts a running preset or dance. Keyboard repeats cannot restart a stopped held command before release. Use a Latin keyboard layout.

## Establish the reference

At the beginning of every connection, put the robot in the same chosen neutral physical pose used during calibration. Choose **Set reference** and confirm. This zeros all three software pulse counters at that pose. Then choose **Arm** or press Enter.

The reference defines pulse position `[0, 0, 0]`. It is manually established. Returning to reference commands the motors back to those three counts and holds there.

Connecting does not move motors. Reconnecting resets the firmware configuration and requires establishing the reference again. Changing motor direction or travel limits in Testing also invalidates the reference and requires setting it again.

## Teach full curl and released poses once

The physical endpoints of your pipak cannot be inferred from a motor model. Hardware configuration therefore ships with the seven motion targets empty. Their buttons are disabled until each target is recorded or entered in Testing.

Each target stores all three cable pulse counts. A two-cable curl has its own independent target, rather than being synthesized by adding two single-cable poses.

In **Testing**, open **Parameters & pose calibration**. The calibration section contains individual hold-to-jog buttons for each cable and a record button for each target.

- Establish the neutral reference in the main window.
- Open the calibration menu and choose **Arm jog**.
- Hold **Take up +** or **Pay out -** for the desired cable. Release to stop.
- Place the robot in the desired full curl for C1, then choose **Disarm**.
- Choose **Record current** beside **Curl C1**.
- Repeat for C2, C3, C1+C2, C2+C3, C3+C1 and the all-cables-released pose.
- Choose **Save & apply** to store the targets in `config.json`.
- Close the menu, return to the main window, and arm again.

For each new pose, use the individual jog controls to adjust all three cable positions as needed. Record after disarming so the counts are stationary. You may also enter the three pulse positions directly.

**Release all** moves to the taught released pose. Choose a released position that pays out the intended amount of cable and leaves the spools manageable. The software cannot detect slack or measure force.

Travel limits default to ±560 pulses, carried over as initial settings from the previous prototype. Check them against the actual motor microstepping, spool and cable travel before teaching endpoints. The parameter menu lets you change each cable's min/max limit and electrical direction sign. Positive counts should always take up cable.

Settings and pose limits are validated together. If a changed travel limit excludes a stored pose, correct or clear that pose before applying. Empty all three fields to clear a target. Partially empty targets are rejected.

In **Operating**, saved targets are used directly and the parameter menu is absent.

## Parameters and response tuning

Testing has one editable menu with the following controls.

| Parameter | Purpose |
|---|---|
| Maximum joystick speed | Pulse rate for an axis-aligned, full-displacement command |
| Centre dead zone | Fraction of joystick radius that commands zero velocity |
| Axes rotation | Rotates the visual rays and the mapping together |
| Three take-up multipliers | Per-cable scaling when winding cable |
| Three pay-out multipliers | Per-cable scaling when releasing cable |
| Preset speed | Maximum rate used when approaching a taught pose |
| Calibration jog speed | Individual jog button rate |
| Pose timeout | Maximum allowed time per target |
| Motor direction signs | +1/-1 logical-to-electrical direction |
| Travel limits | Absolute pulse bounds relative to the manual reference |
| Dance amplitude, speed and cycles | Size, speed and repetition of the small gesture |
| Seven sets of three pulse counts | Full-curl and release targets |

Use **Apply** for the current session, or **Save & apply** to persist the complete validated configuration. Editing applies without restarting Python. Applying disarms motion, so return to the main window and arm again.

The hardware configuration is `config.json`. Simulation uses and saves `config.simulation.json` separately. Simulation initially creates sample curl targets only in memory, and saving simulation settings writes that separate file. Demo poses therefore do not overwrite real robot calibration.

The firmware rate limit is 1000 STEP pulses/s per motor. Joystick speed multiplied by every take-up/pay-out gain must stay within that bound. Increasing pulse speed increases rotation speed with the same microstep setting and spool. Different driver microstep settings require gain or hardware adjustments to obtain equal cable travel.

## Presets and dance

The six curl buttons and Release all execute the saved absolute three-cable targets. Return to reference targets `[0,0,0]`. Rates slow near the target and stop when the emitted counts match. Limits and timeouts cancel a motion.

**Dance** runs a short sequence of small opposing cable movements around the current pose, then returns to that starting pose. Defaults are 12-pulse amplitude, 220 pulses/s maximum and two cycles. It is a small gesture whose physical size depends on microstepping and spool radius.

Before dance starts, the complete sequence is checked against travel limits. Near a limit it is rejected as a whole instead of clipping only one cable. Space, manual joystick input, focus loss and disarm interrupt it. An interrupted dance holds its current pose and cancels the remainder.

## Connection and stopping behavior

A dedicated worker owns USB communication and the pulse-position motion planner. The GUI never waits for a serial reply. While armed, the worker sends fresh velocity commands at approximately 20 Hz.

The firmware stops and disarms after 400 ms without a fresh velocity packet. Separately, the worker disarms if the GUI stops updating its intent for 250 ms. Parameter dialogs and reference confirmation no longer own the serial heartbeat. Native Tk dialog focus is handled without the earlier `__tk__messagebox` crash.

A travel limit stops all cables. Release controls, arm, then move inward from the limit. The controller never automatically re-arms after an error. A serial failure displays the actual failed command and message, disarms when communication permits, and requires closing and reconnecting.

Positions are counts of emitted pulses. Slip, missed steps, cable stretch and changing spool radius create physical error that the software cannot measure. Establish the reference again after any change that invalidates those counts. The controller uses constant pulse rates with immediate starts and reversals, so use rates the loaded mechanism can follow.

## Files

| File | Purpose |
|---|---|
| `app.py` | Launcher, joystick interface and Testing parameter menu |
| `engine.py` | Communication worker, stops and position-target planner |
| `settings.py` | Configuration validation, joystick mapping and dance sequence |
| `transport.py` | Existing RKR3 serial protocol and simulator |
| `config.json` | Hardware parameters and taught poses |
| `run_operating.py` / `run_testing.py` | Mode-specific Python entry points |
| `Start_*.sh` / `Start_*.cmd` | Mode-specific launch scripts |
| `Setup_Linux.sh` / `Setup_Windows.cmd` | Environment setup and shortcut installation |
| `install_shortcuts.py` | Native .desktop or Windows .lnk generation |
| `assets/` | PNG and ICO launcher icons |
| `firmware/rkr_3cable/rkr_3cable.ino` | Matched Arduino firmware |

## Verification

The implementation was exercised in simulation for the three 120° axes, opposite directions, continuous mixing, radial speed, dead zone, all seven pose targets, exact reference return, dance, manual cancellation, limits and GUI-intent expiry.

A compiled native harness of the included firmware was connected through a pseudo-terminal to the new Python worker. Serial handshake, joystick rates, exact pulse-target return, a two-cable curl, interrupted dance and automatic disarm on a paused GUI were exercised.

The GUI was opened on a graphical display and visually reviewed. Automated interactions exercised dragging/releasing, keyboard stop handling, the Testing menu, recording and saving targets, validation and native confirmation dialog focus.

Linux shortcut generation and launch script syntax were checked. Windows launcher and shortcut source was reviewed; Windows execution and physical robot behavior remain to be verified on your devices.
