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

## Start here: what you are setting up

There are two separate programs: Python runs on your computer and provides the keyboard window; Arduino firmware runs on the board and generates motor pulses. Installing Python does not upload firmware. First test the Python window in simulation, then upload firmware and connect the robot.

Follow the **Linux Mint** or **Windows** path below. Commands are entered in a terminal, one block at a time, followed by Enter. Do not type the surrounding Markdown backticks or a terminal prompt such as `$` or `PS>`.

### The pieces and why they matter

| Term | Meaning in this project |
|---|---|
| Terminal | A window for entering commands and reading output |
| Shell | Interprets commands: Bash on Mint; PowerShell or Command Prompt on Windows |
| Current directory | The folder in which the terminal is currently working |
| Python interpreter | The executable that runs `.py` source files |
| Module / package | Python code loaded with `import`; some comes with Python and some must be installed |
| `pip` | Python's package installer |
| `.venv` | A folder containing this project's virtual environment and installed packages |
| Activation | Makes this terminal use the project's Python when you type `python` |
| `requirements.txt` | The list of extra Python packages needed by the project |

Two independent questions help diagnose most problems: **Which folder is this terminal in? Which Python is it using?** Activating an environment changes Python selection; it does not change the current folder.

A virtual environment keeps project dependencies separate. Create it once in the project folder and reuse it. Activation is only for the current terminal session. It is also possible to use the environment's Python by its full path without activation. Recreate environments on other computers or after moving the project; do not copy a Linux environment to Windows. See the [official venv documentation](https://docs.python.org/3/library/venv.html).

### Prepare the project files — both operating systems

If you received an archive, extract it before running anything. If you received individual files, put them together in a permanent project folder. Do not run from an archive preview.

The folder you open must contain all of these files at the same level:

- `keyboard_control.py`
- `controller.py`
- `motion.py`
- `transport.py`
- `config.json`
- `requirements.txt`

Keep `firmware/rkr_controller/rkr_controller.ino` in its firmware subfolders. Choose a location you can write to, such as a project folder under your home directory or Documents. Avoid moving it after creating shortcuts. Your folder may have a different name from `rkr_keyboard_v1`; that is fine.

The tutorial uses Python **3.10 or newer**. Tkinter supplies the window. The additional dependency is `pyserial`, used for Arduino communication. Camera packages, OpenCV, MediaPipe and the global `keyboard` package are unnecessary for this version.

## Linux Mint: initial setup from scratch

### Check Python and install system support

Open Terminal with **Ctrl+Alt+T**:

```bash
python3 --version
```

You should see `Python 3.x.x`, with version 3.10 or newer. Mint generally already includes Python. If it is older, stop here and check your Mint version rather than replacing the system Python manually.

Install the supporting packages:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip python3-tk
```

`apt` installs operating-system packages. `update` refreshes the available-package list; `install` installs the named packages. `sudo` grants administrator privileges for this system setup. The password does not appear while you type. Later project commands do not need sudo.

`python3-venv` provides environment creation, `python3-pip` provides the package installer, and `python3-tk` provides the graphical toolkit.

### Open a terminal in the correct folder

In the file manager, open the project folder where you can see `keyboard_control.py`. Right-click an empty area and choose **Open in Terminal**.

Check your location and files:

```bash
pwd
ls
```

`pwd` prints the current directory; `ls` lists its contents. If `keyboard_control.py` is not listed, you are in the wrong folder.

Alternatively, navigate with `cd`, using your actual path:

```bash
cd "$HOME/Documents/rkr_keyboard_v1"
```

This is an example, not a guaranteed location on your laptop. `cd` changes directory; double quotes handle spaces in the path. `cd ..` goes up one directory.

### Create and activate the environment

Run from the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

The first command uses Python's `venv` module (`-m` means “run a module”) to create the `.venv` folder. The second activates it in this terminal. A successful creation often prints nothing.

Your prompt usually starts with `(.venv)`. Verify the interpreter:

```bash
which python
python -c "import sys; print(sys.executable)"
```

Both should point inside your project's `.venv/bin/`. `-c` runs the short Python statement inside the quotation marks. The `.venv` folder is hidden in Mint's file manager; press **Ctrl+H** to show it.

### Install dependencies and check imports

```bash
python -m pip install -r requirements.txt
python -c "import tkinter; import serial; print('Dependencies OK')"
```

`python -m pip` uses the package installer belonging to the selected interpreter. `-r requirements.txt` tells it to read the dependency list. Packages are installed into `.venv`.

The second command should print `Dependencies OK`. `pyserial` is the installed package name, but its import name is `serial`. Tkinter comes from the Mint system package; `csv`, `json` and `time` are included with Python.

### Open the simulation

```bash
python keyboard_control.py --sim
```

The shell starts Python, Python executes the script, and our script interprets `--sim` as simulation mode. Follow **First window test** below. Leave the terminal open while the window is running.

### Connect the Arduino on Linux

Complete **Upload the Arduino firmware** below first. Close Serial Monitor, then list ports:

```bash
python -m serial.tools.list_ports
```

With this project's expected USB port:

```bash
python keyboard_control.py --port /dev/ttyUSB0
```

Use the listed device if it differs, for example `/dev/ttyACM0`. If several devices are listed, identify the Arduino; compare the list before and after plugging it in.

If opening the device produces **Permission denied**, inspect its group:

```bash
ls -l /dev/ttyUSB0
groups
```

On Mint it is commonly `dialout`. If the device belongs to `dialout` and your account is not a member:

```bash
sudo usermod -aG dialout "$USER"
```

Log out of your desktop session completely and log back in, then reopen the project terminal and activate `.venv` again. Group membership does not update in an already-running session. Do not run the robot application with sudo or change the serial device to world-writable permissions.

### Every later Linux session

Open a terminal in the project folder, then:

```bash
source .venv/bin/activate
python keyboard_control.py --port /dev/ttyUSB0
```

For simulation, substitute `--sim` for `--port /dev/ttyUSB0`. You do not recreate `.venv` or reinstall packages every time. Type `deactivate` to leave the environment, or close the terminal after quitting the application.

You can also launch without activation:

```bash
.venv/bin/python keyboard_control.py --port /dev/ttyUSB0
```

### Optional Linux double-click launcher

If you have `launch_robot.sh`, put it **inside the project folder**, next to `keyboard_control.py` and `.venv`. Grant execution permission once:

```bash
chmod +x launch_robot.sh
```

Then double-click it and choose **Run**, or launch it from the terminal:

```bash
./launch_robot.sh
```

It selects `.venv/bin/python` and `/dev/ttyUSB0` automatically. It still requires the installed dependencies and matching Arduino firmware. It does not automatically reference, arm or move the robot.

**Do not copy the shell script onto the Desktop.** It finds the project relative to its own location. To create a desktop shortcut on Mint, right-click the Desktop, choose **Create a new launcher here…**, give it a name and browse to the script in the project folder. If the project path contains spaces, quote the full script path in the launcher's Command field. The desktop item should point to the script, which stays in the project folder.

If Mint opens the script in an editor, use `./launch_robot.sh` or adjust the file manager's executable-text-file preference. Startup failures are recorded in `logs/launcher_startup.log`; read it with:

```bash
cat logs/launcher_startup.log
```

## Windows: initial setup from scratch

### Install or check Python

Open **PowerShell** from the Start menu and run:

```powershell
python --version
```

If this reports Python 3.10 or newer, continue. If it is unavailable, try:

```powershell
py --version
```

If neither works, install Python from [python.org/downloads](https://www.python.org/downloads/), following the Windows instructions offered there. The current official route uses the Python install manager. If you use a traditional Python installer, enable **Add Python to PATH** and include **pip** and **Tcl/Tk**. Close and reopen PowerShell after installation, then check the version again. See [Python's Windows setup documentation](https://docs.python.org/3/using/windows.html).

The commands below use `python` to create the environment. If only `py` works, use `py -m venv .venv` for that creation step. After activation, use `python` as shown.

### Open PowerShell in the project folder

Extract or collect the files as described above. Open that folder in File Explorer. Click the address bar, type `powershell`, and press Enter. This opens PowerShell at that location.

Verify:

```powershell
Get-Location
Get-ChildItem
```

The first prints the current folder; the second lists its files. Confirm that `keyboard_control.py` is listed. You can also navigate using your actual folder path:

```powershell
cd "$HOME\Documents\rkr_keyboard_v1"
```

This is an example; Documents may be elsewhere, including under OneDrive. Opening PowerShell from File Explorer avoids guessing the path. Quotes allow spaces in folder names.

### Create and activate the environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

The first command creates `.venv` inside the project. Windows keeps its interpreter in `Scripts`, while Linux uses `bin`. Activation usually adds `(.venv)` to the prompt.

If PowerShell reports that **running scripts is disabled**, you can continue without activation or any execution-policy changes. Run the interpreter explicitly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -c "import tkinter; import serial; print('Dependencies OK')"
.\.venv\Scripts\python.exe keyboard_control.py --sim
```

Those three commands complete installation, check dependencies and start simulation. Skip the equivalent activated commands below if you already ran them. There is no need to weaken a machine-wide policy.

Alternatively, open **Command Prompt** in the same project folder by typing `cmd` into File Explorer's address bar. Its activation command is:

```bat
.venv\Scripts\activate.bat
```

Use that command in Command Prompt, not PowerShell. After activation in either shell, check Python:

```powershell
python -c "import sys; print(sys.executable)"
```

The path should end with your project's `.venv\Scripts\python.exe`.

### Install dependencies and open simulation

In the activated environment:

```powershell
python -m pip install -r requirements.txt
python -c "import tkinter; import serial; print('Dependencies OK')"
python keyboard_control.py --sim
```

Expect `Dependencies OK` followed by the control window. If Tkinter is missing, modify/reinstall your Windows Python installation with Tcl/Tk support; it is not installed by `pip install tkinter`.

Follow **First window test** below. Leave PowerShell open while the application runs.

### Connect the Arduino on Windows

Complete **Upload the Arduino firmware** below first and close Serial Monitor. In your project environment:

```powershell
python -m serial.tools.list_ports
```

Find the board's COM port. It also appears in Arduino IDE's port selector or Windows Device Manager under **Ports (COM & LPT)**. If it is COM3:

```powershell
python keyboard_control.py --port COM3
```

Replace COM3 with the actual port, such as COM5. Without activation, the equivalent is:

```powershell
.\.venv\Scripts\python.exe keyboard_control.py --port COM3
```

If no port appears, check the USB cable can carry data and that the board appears in Device Manager. Some USB-serial boards require a driver appropriate to their USB interface; identify that interface and use its manufacturer's driver rather than an unrelated download.

### Every later Windows session

Open PowerShell in the project folder:

```powershell
.\.venv\Scripts\Activate.ps1
python keyboard_control.py --port COM3
```

Or bypass activation:

```powershell
.\.venv\Scripts\python.exe keyboard_control.py --port COM3
```

Use your actual COM port. For simulation, use `--sim`. Reinstalling dependencies is only needed if the environment is recreated or the requirements change. `deactivate` leaves an activated environment.

The supplied `launch_robot.sh` is for Linux. On Windows, use the terminal commands above; this README does not include a Windows executable launcher.

## First window test — both operating systems

Start with simulation. When the control window opens, click inside it so it receives keyboard events.

1. Press **Z** and confirm the reference dialog. In simulation this declares `[0,0]`; on hardware it must correspond to a deliberately established physical reference.
2. Press **Enter** to arm. Check the display says ARMED.
3. Briefly hold **R**, then release it: motor 1's counter should increase and stop. **E** reverses it. **M/N** control motor 2.
4. Try the arrows, then **J/L** and **1/2/3** in simulation to see their behavior.
5. Press **Space** to cancel a movement. Press **Escape** to disarm. Release all held keys before starting again.
6. Press **Q** to close the program and return to the terminal prompt.

Clicking another window disarms the controller. After returning, press Enter to arm again. Simulation verifies the controls and program setup; it does not model robot shape, slack, current or mechanical load. A serial failure never silently switches hardware mode to simulation.

## Upload the Arduino firmware — both operating systems

Install [Arduino IDE](https://www.arduino.cc/en/software) if needed. Connect the Arduino by USB, then open **`firmware/rkr_controller/rkr_controller.ino`**. Select your actual board and USB port in the IDE. Install the board support package if prompted, compile and upload, and wait for a successful upload message.

Upload this project's replacement sketch, not a file from `legacy/`. It has no external Arduino library dependencies. Do not leave an older Python controller running during upload. Close Arduino Serial Monitor and Serial Plotter before launching Python; they can occupy the same serial port.

Wiring follows the original sketches:

| Signal | Motor 1 | Motor 2 |
|---|---:|---:|
| STEP | D2 | D5 |
| DIR | D3 | D6 |
| ENABLE | D4 | D7 |

Serial baud rate is **115200**. Enable is assumed active LOW; confirm the actual driver input polarity and wiring. Change `ENABLE_ACTIVE` in the sketch if required. NEMA 17 specifies the motor frame, not the electrical rating or exact driver.

Python checks for protocol **`RKR 1`**. Incompatible firmware is refused. Opening the port can reset the board. Every application session needs a new reference; a previous CSV does not establish the robot's present physical position.

After simulation succeeds and firmware is uploaded, use your operating system's hardware launch command above. Continue with **Establish the reference and verify directions** before running any full motion.

## Troubleshooting installation and startup

| Symptom | What to check or do |
|---|---|
| `can't open file ... keyboard_control.py` | Wrong current directory. Use `pwd`/`ls` on Linux or `Get-Location`/`Get-ChildItem` in PowerShell. |
| `No module named serial` | Install requirements with the exact environment interpreter: `.venv/bin/python -m pip install -r requirements.txt` on Linux or `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` on Windows. |
| `No module named controller` or `motion` | Keep all project Python files together; the main script is not standalone. |
| `No module named tkinter` | Mint: install `python3-tk`. Windows: include Tcl/Tk in your Python installation. |
| `externally-managed-environment` during pip installation | On Mint, use the project `.venv`; do not force pip to modify system Python. |
| `ensurepip` unavailable during environment creation | Mint: install `python3-venv`; if the error names a matching version-specific venv package, install that package for your chosen interpreter. Retry environment creation. |
| PowerShell blocks `Activate.ps1` | Use `.\.venv\Scripts\python.exe` directly as shown above. |
| `>>>` appears instead of a shell prompt | You opened Python interactively. Type `exit()` to return to the shell before entering terminal commands. |
| `Permission denied` on `/dev/ttyUSB0` | Follow the Linux serial-group steps and fully log out/in. |
| COM port access denied / device busy | Close Serial Monitor, Serial Plotter and other controllers; check no previous copy is still running. |
| Port does not exist | Re-list ports after connecting USB; use the actual device name. |
| Protocol error / upload firmware message | Confirm the correct board, port and replacement sketch; close the app and retry after upload. |
| Launcher says `.venv` missing | Keep `launch_robot.sh`, `.venv` and `keyboard_control.py` in the same project folder. A Desktop copy of the script looks in the wrong place. |
| Settings file not found or invalid | Keep `config.json` beside the main script; check JSON syntax and parameter limits. |

To inspect the selected environment in either OS after activation:

```text
python -c "import sys; print(sys.executable)"
python -m pip list
```

If it still fails, record the command, its complete output, the interpreter path and your operating system. Keep your calibrated `config.json` and source files when fixing an environment. Do not delete a working environment just because activation was skipped; try its explicit interpreter path first.

When sharing the project, share source and requirements, and create a fresh `.venv` on each machine. A shortcut only launches an existing installation; it does not replace setup or upload firmware.


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
