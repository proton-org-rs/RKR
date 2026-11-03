#!/usr/bin/env python3
"""RKR keyboard tester. Start: python keyboard_control.py --sim
Hardware: python keyboard_control.py --port COM3 (or /dev/ttyUSB0).
Read README.md before motor testing. Edit config.json, then restart to customize.
"""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import tkinter as tk
from tkinter import messagebox
from controller import Controller
from motion import load_config
from transport import SerialLink, SimLink

MANUAL = {'r', 'e', 'm', 'n', 'Left', 'Right'}


class Application:
    def __init__(self, root, link, cfg, simulation, log_dir):
        self.root, self.link, self.cfg = root, link, cfg
        self.pressed = set()
        self.releases = {}
        self.failed = False
        self.stop_latch = False
        self.closing = False
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        prefix = log_dir / stamp
        Path(str(prefix) + '_config.json').write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        self.logfile = Path(str(prefix) + '.csv').open('w', newline='', encoding='utf-8')
        self.writer = csv.writer(self.logfile)
        self.writer.writerow(['utc', 'monotonic_s', 'mode', 'command', 'm1_pulses', 'm2_pulses',
                              'm1_revolutions', 'm2_revolutions', 'busy', 'armed', 'referenced'])
        self.simulation = simulation
        self.control = Controller(link, cfg, self.record)
        root.title('RKR • Keyboard test v1 • ' + ('SIMULATION' if simulation else 'HARDWARE'))
        root.geometry('810x540')
        root.configure(bg='#15202b')
        self.heading = tk.Label(root, text='SIMULATION — no hardware connected' if simulation else 'HARDWARE — STEP pulse estimates',
                                bg='#15202b', fg='#60d4d0', font=('Arial', 18, 'bold'))
        self.heading.pack(pady=(20, 10))
        self.readout = tk.Label(root, bg='#15202b', fg='white', justify='left', font=('Courier', 16))
        self.readout.pack(pady=10)
        self.notice = tk.StringVar(value='Set a known neutral pose. Z = reference zero, then Enter = arm.')
        tk.Label(root, textvariable=self.notice, wraplength=760, bg='#15202b', fg='#ffca70', font=('Arial', 12)).pack(pady=10)
        help_text = (
            'HOLD  R / E       Motor 1 tighten / release\n'
            'HOLD  M / N       Motor 2 tighten / release\n'
            'HOLD  ← / →       Swing left / right (release ratio A)\n'
            'PRESS J / L       Curl left / right to calibrated targets\n'
            'PRESS 1 / 2 / 3   Run configured sequence\n'
            'PRESS H           Return to reference zero (not physical homing)\n'
            'SPACE             Stop motion + cancel sequence; retain holding torque\n'
            'ESC / ENTER       Disarm / arm motion\n'
            'Z / Q             Establish zero / quit')
        tk.Label(root, text=help_text, justify='left', bg='#15202b', fg='#d5dfe7', font=('Courier', 12)).pack(pady=10)
        tk.Label(root, text='Keep this window focused. Focus loss disarms. Edit config.json and restart to customize.',
                 bg='#15202b', fg='#a3b7c7', wraplength=760).pack()
        root.bind('<KeyPress>', self.on_press)
        root.bind('<KeyRelease>', self.on_release)
        root.bind('<FocusOut>', self.focus_lost)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, root.focus_force)
        root.after(50, self.tick)

    def record(self, command, state):
        LOG_INTERVAL = 0.5  # seconds: 0.5 = 2 samples/s; 1.0 = 1 sample/s

        if command == 'STATE' or command.startswith('MOVE '):
            now = time.monotonic()
            if now - getattr(self, '_last_sample_log', float('-inf')) < LOG_INTERVAL:
                return
            self._last_sample_log = now
        spr = self.cfg['steps_per_revolution']
        self.writer.writerow([datetime.now(timezone.utc).isoformat(), f'{time.monotonic():.6f}',
                              'simulation' if self.simulation else 'hardware', command,
                              state.p1, state.p2, state.p1 / spr[0], state.p2 / spr[1],
                              int(state.busy), int(state.armed), int(state.referenced)])
        self.logfile.flush()

    def clear_keys(self):
        for job in self.releases.values():
            self.root.after_cancel(job)
        self.releases.clear()
        self.pressed.clear()
        self.stop_latch = False

    def fault(self, exc):
        self.failed = True
        self.clear_keys()
        self.control.queue.clear()
        try:
            self.control.stop(disarm=True)
        except Exception:
            pass
        self.notice.set(f'CONNECTION FAULT: {exc}. Motion locked. Close and reconnect; re-establish zero.')

    def perform(self, fn):
        if self.failed:
            return
        try:
            fn()
        except ValueError as exc:
            self.notice.set(str(exc))
        except Exception as exc:
            self.fault(exc)

    @staticmethod
    def key(event):
        return event.keysym.lower() if len(event.keysym) == 1 else event.keysym

    def on_press(self, event):
        key = self.key(event)
        if key in self.releases:
            self.root.after_cancel(self.releases.pop(key))
        if key in self.pressed:
            return  # ignore OS key repeat for one-shot actions
        self.pressed.add(key)
        if key == 'q':
            self.close()
            return
        if self.failed:
            return
        if key in ('space', 'Escape'):
            self.stop_latch = True
            self.perform(lambda: self.control.stop(disarm=key == 'Escape'))
            self.notice.set('Stopped. Release keys before starting a new motion.')
        elif self.stop_latch:
            return
        elif key == 'Return':
            self.perform(self.control.arm)
        elif key == 'z':
            self.perform(self.establish_zero)
        elif key in MANUAL:
            self.perform(lambda: self.control.manual(self.pressed & MANUAL))
        elif key in ('j', 'l', 'h', '1', '2', '3'):
            self.perform(lambda: self.control.start_action(key))
            self.notice.set(f'Action {key}: Space cancels at any time.')

    def on_release(self, event):
        key = self.key(event)
        if key in self.releases:
            self.root.after_cancel(self.releases[key])
        # X11 may emit release/press pairs during repeat. Defer release briefly.
        self.releases[key] = self.root.after(35, lambda: self.finish_release(key))

    def finish_release(self, key):
        self.releases.pop(key, None)
        self.pressed.discard(key)
        if not self.pressed:
            self.stop_latch = False
        if key in MANUAL and self.control.mode == 'manual':
            self.perform(lambda: self.control.manual(self.pressed & MANUAL))

    def establish_zero(self):
        if self.control.state.armed or self.control.state.busy:
            raise ValueError('Press Escape to disarm before setting zero.')
        if messagebox.askyesno('Set physical reference',
                              'Is the robot in its known neutral pose, with both cables gently tensioned?\n'
                              'This resets both counters; it does not move or home the motors.'):
            self.control.zero()
            self.notice.set('Reference set. Press Enter to arm. Verify motor directions with short taps.')
        self.clear_keys()

    def focus_lost(self, event):
        if not self.closing:
            self.clear_keys()
            self.perform(lambda: self.control.stop(disarm=True))
            self.notice.set('Window lost focus: disarmed. Click here and press Enter to resume.')

    def tick(self):
        if self.closing:
            return
        self.perform(self.control.tick)
        s = self.control.state
        spr = self.cfg['steps_per_revolution']
        self.readout.config(text=(f'M1 {s.p1:+7d} pulses   {s.p1/spr[0]:+8.4f} rev\n'
                                  f'M2 {s.p2:+7d} pulses   {s.p2/spr[1]:+8.4f} rev\n'
                                  f'{"ARMED" if s.armed else "DISARMED":10} '
                                  f'{"MOVING" if s.busy else "STOPPED":10} A={self.cfg["A"]:g}\n'
                                  f'Reference: {"SET" if s.referenced else "NOT SET"}   Action: {self.control.mode}'))
        self.root.after(50, self.tick)

    def close(self):
        if self.closing:
            return
        self.closing = True
        try:
            self.control.stop(disarm=True)
        except Exception:
            pass
        finally:
            self.link.close()
            self.logfile.close()
            self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--sim', action='store_true', help='Explicit hardware-free simulation')
    group.add_argument('--port', help='Explicit Arduino serial port, e.g. COM3 or /dev/ttyUSB0')
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('config.json'))
    parser.add_argument('--log-dir', type=Path, default=Path(__file__).with_name('logs'))
    args = parser.parse_args()
    link = None
    root = None
    try:
        cfg = load_config(args.config)
        link = SimLink() if args.sim else SerialLink(args.port)
        root = tk.Tk()
        app = Application(root, link, cfg, args.sim, args.log_dir)
        try:
            root.mainloop()
        finally:
            app.close()
    except Exception as exc:
        print(f'Cannot start: {exc}', file=sys.stderr)
        if link:
            try:
                link.request('DISARM')
            except Exception:
                pass
            link.close()
        if root:
            try:
                root.destroy()
            except tk.TclError:
                pass
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
