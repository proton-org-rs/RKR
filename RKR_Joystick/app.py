#!/usr/bin/env python3
"""SpiRob joystick application. Start with python app.py; --mode testing or operating."""
import argparse
from copy import deepcopy
import math
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox

from engine import Engine
from settings import AXES, POSES, load, save, validate, joystick_rates, demo_config

ROOT = Path(__file__).resolve().parent
BG = "#0b1218"
PANEL = "#131e27"
EDGE = "#263843"
WHITE = "#edf2ee"
MUTED = "#91a5af"
TEAL = "#69dfbf"
ORANGE = "#f2a371"
RED = "#ff7d79"
FONT = "Segoe UI" if sys.platform == "win32" else "DejaVu Sans"


def text(parent, label, size=11, color=WHITE, bold=False, bg=None, **kwargs):
    return tk.Label(parent, text=label, font=(FONT, size, "bold" if bold else "normal"),
                    fg=color, bg=bg or parent.cget("bg"), **kwargs)


def button(parent, label, command, accent=False, danger=False, **kwargs):
    color = RED if danger else (TEAL if accent else EDGE)
    foreground = BG if accent or danger else WHITE
    widget = tk.Button(parent, text=label, command=command, bg=color, fg=foreground,
                       activebackground="#354e5c" if not accent else "#9df2d6",
                       activeforeground=foreground, relief="flat", bd=0,
                       font=(FONT, 10, "bold"), cursor="hand2", padx=16, pady=12,
                       highlightthickness=1, highlightbackground=color, **kwargs)
    widget.bind("<Enter>", lambda event: widget.configure(highlightbackground=TEAL))
    widget.bind("<Leave>", lambda event: widget.configure(highlightbackground=color))
    return widget


def entry(parent, variable, width=9):
    return tk.Entry(parent, textvariable=variable, width=width, bg=BG, fg=WHITE,
                    insertbackground=TEAL, relief="flat", font=(FONT, 11),
                    highlightthickness=1, highlightbackground=EDGE, highlightcolor=TEAL)


def brand(canvas, cx, cy, radius):
    points = []
    for n in range(420):
        angle = n/419*math.pi*4.2
        r = radius * (0.06 + 0.94*n/419)
        points.extend((cx+r*math.cos(angle), cy+r*math.sin(angle)))
    canvas.create_line(points, fill=TEAL, width=4, smooth=True)
    canvas.create_oval(cx-4, cy-4, cx+4, cy+4, fill=ORANGE, outline="")


class Launcher:
    def __init__(self, root, mode=None, simulation=False, port=None):
        self.root = root
        self.mode = mode
        self.result = None
        cfg = load(ROOT/"config.json")
        self.port = tk.StringVar(value=port or cfg["port"])
        self.simulation = tk.BooleanVar(value=simulation)
        root.title("SpiRob · Control room")
        root.configure(bg=BG)
        root.geometry("1000x680")
        root.minsize(900, 650)
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        left = tk.Frame(root, bg=BG, padx=42, pady=35)
        left.grid(row=0, column=0, sticky="nsew")
        text(left, "R K R   /   R O B O T I C S", 10, TEAL, True).pack(anchor="w")
        art = tk.Canvas(left, width=360, height=270, bg=BG, highlightthickness=0)
        art.pack(pady=(10, 0))
        for r in (74, 110, 138):
            art.create_oval(180-r, 135-r, 180+r, 135+r, outline=EDGE)
        brand(art, 180, 135, 116)
        text(left, "A softer way\nto move.", 32, WHITE, True, justify="left").pack(anchor="w", pady=12)
        text(left, "Three cables. One continuous gesture.", 11, MUTED).pack(anchor="w")
        text(left, "SPIROB  /  CONTROL ROOM  02", 9, MUTED, True).pack(anchor="w", pady=(35, 0))
        right = tk.Frame(root, bg=PANEL, padx=34, pady=40)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 24), pady=24)
        text(right, "Choose your workspace", 19, bold=True).pack(anchor="w")
        text(right, "Mouse joystick  •  Keyboard  •  Taught poses", 10, MUTED).pack(anchor="w", pady=(8, 26))
        choices = (("operating", "OPERATE", "A focused control surface for the exhibit."),
                   ("testing", "TEST & CALIBRATE", "Tune the response and record robot poses."))
        for name, title, subtitle in choices:
            if mode is not None and name != mode:
                continue
            card = tk.Frame(right, bg=BG, padx=18, pady=16, highlightthickness=1, highlightbackground=EDGE)
            card.pack(fill="x", pady=(0, 14))
            text(card, title, 13, TEAL if name=="operating" else ORANGE, True).pack(anchor="w")
            text(card, subtitle, 10, MUTED, wraplength=330, justify="left").pack(anchor="w", pady=(7, 14))
            button(card, "Open workspace  →", lambda selected=name: self.launch(selected), accent=name=="operating").pack(fill="x")
        connection = tk.Frame(right, bg=PANEL)
        connection.pack(fill="x", pady=(10, 0))
        text(connection, "CONTROLLER PORT", 9, MUTED, True).pack(anchor="w")
        entry(connection, self.port, width=28).pack(fill="x", pady=8, ipady=7)
        tk.Checkbutton(connection, text="Simulation · no robot connected", variable=self.simulation,
                       bg=PANEL, fg=WHITE, selectcolor=BG, activebackground=PANEL,
                       activeforeground=TEAL, font=(FONT, 10), highlightthickness=0).pack(anchor="w")
        text(right, "Hold to steer. Release to stay.", 10, MUTED).pack(anchor="w", pady=(22, 0))
        root.rowconfigure(0, weight=1)

    def launch(self, mode):
        self.result = (mode, self.simulation.get(), self.port.get().strip())
        self.root.quit()


class Workspace:
    def __init__(self, root, cfg, config_path, mode, simulation, engine=None):
        self.root, self.cfg, self.config_path = root, cfg, config_path
        self.mode, self.simulation = mode, simulation
        self.engine = engine or Engine(cfg, simulation)
        self.engine.start()
        self.keys, self.releases = set(), {}
        self.inhibited_keys = set()
        self.pointer = None
        self.jog = None
        self.editor = None
        self.closed = False
        self.focused = False
        self.last_rates = (0, 0, 0)
        self.display_vector = (0, 0)
        self.ui_message = ""
        self.pose_buttons = {}
        self.root.title("SpiRob · " + ("Testing" if mode=="testing" else "Operating") +
                        (" · Simulation" if simulation else " · Hardware"))
        root.configure(bg=BG)
        root.geometry("1180x800")
        root.minsize(1040, 740)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.status = tk.StringVar(value="Connecting…")
        self.notice = tk.StringVar(value="")
        self.readout_vars = [tk.StringVar(value="0") for _ in range(3)]
        self.rate_vars = [tk.StringVar(value="0 pulses/s") for _ in range(3)]
        self.build()
        root.bind("<KeyPress>", self.key_press)
        root.bind("<KeyRelease>", self.key_release)
        root.bind("<ButtonRelease-1>", self.mouse_release, add="+")
        root.bind("<FocusOut>", lambda event: root.after_idle(self.focus_check))
        root.bind("<FocusIn>", lambda event: root.after_idle(self.focus_check))
        self.tick_job = root.after(40, self.tick)

    def build(self):
        top = tk.Frame(self.root, bg=BG, padx=30, pady=22)
        top.pack(fill="x")
        text(top, "SPIROB", 24, WHITE, True).pack(side="left")
        text(top, "  /  " + self.mode.upper(), 10, TEAL if self.mode=="operating" else ORANGE, True).pack(side="left", pady=(7, 0))
        badge = "SIMULATION" if self.simulation else self.cfg["port"]
        text(top, badge, 10, MUTED).pack(side="right")
        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=24)
        self.body.columnconfigure(0, weight=5)
        self.body.columnconfigure(1, weight=4)
        self.body.rowconfigure(0, weight=1)
        left = tk.Frame(self.body, bg=PANEL, padx=20, pady=18)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        text(left, "DIRECTION & SPEED", 10, TEAL, True).pack(anchor="w")
        text(left, "Hold and drag to steer", 18, WHITE, True).pack(anchor="w", pady=(7, 0))
        text(left, "Further from centre means faster movement.", 10, MUTED).pack(anchor="w", pady=(5, 0))
        self.canvas = tk.Canvas(left, bg=PANEL, width=500, height=435, highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda event: self.draw_pad())
        self.canvas.bind("<ButtonPress-1>", self.mouse_down)
        self.canvas.bind("<B1-Motion>", self.mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.mouse_release)
        text(left, "CENTRE = HOLD CURRENT POSE", 9, TEAL, True).pack(pady=(0, 10))
        text(left, "Arrows / WASD   ·   1 / 2 / 3 toward a cable", 10, MUTED).pack()
        text(left, "Shift + 1 / 2 / 3 away from a cable", 10, MUTED).pack(pady=(4, 0))
        right = tk.Frame(self.body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        self.state_label = text(right, "", 11, TEAL, True, textvariable=self.status, anchor="w", justify="left")
        self.state_label.pack(fill="x", pady=(0, 14))
        actionbar = tk.Frame(right, bg=BG)
        actionbar.pack(fill="x")
        button(actionbar, "Set reference", self.reference).pack(side="left", fill="x", expand=True, padx=(0, 8))
        button(actionbar, "Arm  ↵", lambda: self.action("arm"), accent=True).pack(side="left", fill="x", expand=True)
        text(right, "MOTION PRESETS", 9, MUTED, True).pack(anchor="w", pady=(23, 10))
        self.home_button = button(right, "↶   Return to reference", lambda: self.action("home"))
        self.home_button.pack(fill="x", pady=(0, 8))
        pose_grid = tk.Frame(right, bg=BG)
        pose_grid.pack(fill="x")
        for i, key in enumerate(("curl_1", "curl_2", "curl_3", "curl_12", "curl_23", "curl_31")):
            widget = button(pose_grid, POSES[key], lambda pose=key: self.action("pose", pose))
            widget.grid(row=i//3, column=i%3, sticky="ew", padx=(0 if i%3==0 else 5, 0), pady=4)
            self.pose_buttons[key] = widget
            pose_grid.columnconfigure(i%3, weight=1)
        misc = tk.Frame(right, bg=BG)
        misc.pack(fill="x", pady=(5, 10))
        release = button(misc, "Release all", lambda: self.action("pose", "release"))
        release.pack(side="left", fill="x", expand=True, padx=(0, 7))
        self.pose_buttons["release"] = release
        button(misc, "✦   Dance", lambda: self.action("dance"), accent=True).pack(side="left", fill="x", expand=True)
        telemetry = tk.Frame(right, bg=PANEL, padx=16, pady=12)
        telemetry.pack(fill="x", pady=(6, 14))
        text(telemetry, "CABLE POSITION  /  EMITTED PULSES", 8, MUTED, True).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        for i in range(3):
            text(telemetry, f"C{i+1}", 10, TEAL, True).grid(row=i+1, column=0, sticky="w", padx=(0, 16))
            text(telemetry, "", 12, WHITE, True, textvariable=self.readout_vars[i], width=7, anchor="e").grid(row=i+1, column=1)
            text(telemetry, "", 9, MUTED, textvariable=self.rate_vars[i], width=18, anchor="e").grid(row=i+1, column=2)
        if self.mode == "testing":
            button(right, "⚙   Parameters & pose calibration", self.open_parameters).pack(fill="x", pady=(0, 10))
        self.stop_button = button(right, "STOP   /   SPACE", self.stop, danger=True)
        self.stop_button.pack(fill="x", side="bottom")
        footer = tk.Frame(self.root, bg=BG, padx=28, pady=16)
        footer.pack(fill="x")
        tk.Label(footer, textvariable=self.notice, wraplength=1000, anchor="w",
                 justify="left", fg=ORANGE, bg=BG, font=(FONT, 10)).pack(fill="x")
        text(footer, "ESC disarms    ·    Focus loss stops    ·    Reference is a manually established neutral pose", 9, MUTED).pack(anchor="w", pady=(7, 0))

    def pad_geometry(self):
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        return width/2, height/2+3, max(45, min(width/2-65, height/2-42))

    def draw_pad(self):
        c = self.canvas
        c.delete("all")
        cx, cy, radius = self.pad_geometry()
        for r, fill in ((radius+18, "#101a22"), (radius, "#182832")):
            c.create_oval(cx-r, cy-r, cx+r, cy+r, fill=fill, outline=EDGE, width=1)
        for factor in (.25, .5, .75):
            r = radius*factor
            c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#243b47", dash=(2, 6))
        for n in range(60):
            angle = n*math.tau/60
            outer = radius+8
            inner = radius+3 if n%5 else radius-2
            c.create_line(cx+inner*math.cos(angle), cy+inner*math.sin(angle),
                          cx+outer*math.cos(angle), cy+outer*math.sin(angle), fill="#47616d", width=1)
        rotation = math.radians(self.cfg["joystick"]["rotation_degrees"])
        for i, (x, y) in enumerate(AXES):
            x, y = x*math.cos(rotation)-y*math.sin(rotation), x*math.sin(rotation)+y*math.cos(rotation)
            c.create_line(cx, cy, cx+x*radius, cy-y*radius, fill="#3c6c71", width=2)
            ex, ey = cx+x*(radius+31), cy-y*(radius+31)
            c.create_text(ex, ey, text=f"C{i+1}", fill=TEAL, font=(FONT, 12, "bold"))
        x, y = self.display_vector
        px, py = cx+x*radius, cy-y*radius
        if math.hypot(x,y)>.02:
            c.create_line(cx, cy, px, py, fill=TEAL, width=3)
            c.create_oval(px-21, py-21, px+21, py+21, fill="#214a49", outline="")
        dead = radius*self.cfg["joystick"]["deadzone"]
        c.create_oval(cx-dead, cy-dead, cx+dead, cy+dead, outline="#62857c")
        c.create_oval(px-11, py-11, px+11, py+11, fill=TEAL, outline="#b2ffe8", width=2)
        c.create_text(cx, cy+radius+32, text=f"{round(min(1,math.hypot(x,y))*100):02d}%  /  SPEED",
                      fill=MUTED, font=(FONT, 9, "bold"))

    def mouse_down(self, event):
        self.canvas.focus_set()
        self.pointer = (event.x, event.y)
        self.mouse_drag(event)

    def mouse_drag(self, event):
        if self.pointer is None:
            return
        cx, cy, radius = self.pad_geometry()
        x, y = (event.x-cx)/radius, (cy-event.y)/radius
        length = max(1, math.hypot(x,y))
        self.pointer = (x/length, y/length)

    def mouse_release(self, event=None):
        if self.pointer is not None or self.jog is not None:
            self.pointer = None
            self.jog = None
            self.engine.steer((0,0,0))

    def clear_input(self):
        self.inhibited_keys.update(self.keys)
        for job in self.releases.values():
            self.root.after_cancel(job)
        self.releases.clear()
        self.keys.clear()
        self.pointer = self.jog = None
        self.engine.steer((0,0,0))

    def stop(self):
        self.clear_input()
        self.engine.request("stop")

    def action(self, operation, value=None):
        self.clear_input()
        self.engine.request(operation, value)

    def reference(self):
        self.action("disarm")
        if messagebox.askyesno("Establish reference",
                               "Place the robot in the chosen neutral pose with cables lightly tensioned.\n\n"
                               "Set all three counters to zero at this physical pose?\n"
                               "Use the same neutral pose used when recording the presets.", parent=self.root):
            self.engine.request("zero")
        self.clear_input()

    def focus_check(self):
        if self.closed:
            return
        try:
            focused = self.root.focus_get()
        except (KeyError, tk.TclError):
            focused = None
        main = focused is not None and focused.winfo_toplevel() == self.root
        calibration = self.editor is not None and focused is not None and focused.winfo_toplevel() == self.editor.window
        if self.focused and not (main or calibration):
            self.action("disarm")
        if not main and self.pointer is not None:
            self.action("disarm")
        self.focused = main or calibration

    def key_press(self, event):
        if event.widget.winfo_toplevel() != self.root:
            return
        key = event.keysym.lower()
        if key in self.inhibited_keys:
            return
        if key in self.releases:
            self.root.after_cancel(self.releases.pop(key))
        if key in self.keys:
            return
        self.keys.add(key)
        if key == "space":
            self.stop()
        elif key == "escape":
            self.action("disarm")
        elif key == "return":
            self.action("arm")
        elif key == "home":
            self.action("home")

    def key_release(self, event):
        key = event.keysym.lower()
        self.inhibited_keys.discard(key)
        if key in self.releases:
            self.root.after_cancel(self.releases[key])
        self.releases[key] = self.root.after(30, lambda: self.release_key(key))

    def release_key(self, key):
        self.releases.pop(key, None)
        self.keys.discard(key)

    def vector(self):
        if self.pointer is not None:
            return self.pointer
        # Keyboard vector changes are continuous while held.
        x = int(bool(self.keys & {"right", "d"})) - int(bool(self.keys & {"left", "a"}))
        y = int(bool(self.keys & {"up", "w"})) - int(bool(self.keys & {"down", "s"}))
        for i, name in enumerate(("1", "2", "3")):
            shifted = ("exclam", "at", "numbersign")[i] in self.keys
            if name in self.keys or shifted:
                sign = -1 if shifted or self.keys & {"shift_l", "shift_r"} else 1
                angle = math.radians(self.cfg["joystick"]["rotation_degrees"])
                axis_x, axis_y = AXES[i]
                x += sign*(axis_x*math.cos(angle)-axis_y*math.sin(angle))
                y += sign*(axis_x*math.sin(angle)+axis_y*math.cos(angle))
        radius = max(1, math.hypot(x,y))
        return x/radius, y/radius

    def tick(self):
        if self.closed:
            return
        try:
            self.focus_check()
            self.engine.heartbeat()
            self.display_vector = self.vector()
            rates = joystick_rates(*self.display_vector, self.cfg)
            if self.jog is not None:
                rates = tuple(self.jog[1]*round(self.cfg["motion"]["jog_speed"]*1000) if i==self.jog[0] else 0 for i in range(3))
            self.engine.steer(rates)
            state, message, connected, failed, action = self.engine.snapshot()
            self.status.set("FAULT · RECONNECT" if failed else
                            ("CONNECTING…" if not connected else ("ARMED" if state.armed else "DISARMED") + "  /  " + action.upper()))
            self.notice.set(message)
            for i, (position, rate) in enumerate(zip(state.position, state.rates)):
                self.readout_vars[i].set(f"{position:+d}")
                self.rate_vars[i].set(f"{rate/1000:+.1f} pulses/s")
            for key, widget in self.pose_buttons.items():
                widget.configure(state="normal" if self.cfg["poses"][key] is not None and connected and not failed else "disabled")
            if self.last_rates != rates:
                self.last_rates = rates
                self.draw_pad()
        finally:
            if not self.closed:
                self.tick_job = self.root.after(30, self.tick)

    def open_parameters(self):
        self.action("disarm")
        if self.editor is not None:
            self.editor.window.lift()
            return
        self.editor = Parameters(self)

    def close(self):
        if self.closed:
            return
        self.clear_input()
        self.engine.request("disarm")
        self.engine.close()
        self.closed = True
        self.root.after_cancel(self.tick_job)
        self.engine.join(timeout=1)
        self.root.destroy()


class Parameters:
    def __init__(self, app):
        self.app = app
        self.window = tk.Toplevel(app.root)
        self.window.title("SpiRob · Parameters & calibration")
        self.window.configure(bg=BG)
        self.window.geometry("870x730")
        self.window.minsize(780, 600)
        self.vars = []
        self.pose_vars = {}
        self.feedback = tk.StringVar(value="Edits apply together with Apply. Save persists the validated configuration.")
        header = tk.Frame(self.window, bg=BG, padx=22, pady=18)
        header.pack(fill="x")
        text(header, "PARAMETERS & CALIBRATION", 17, TEAL, True).pack(anchor="w")
        text(header, "Disarm before recording a pose. Take up = positive pulse count.", 10, MUTED).pack(anchor="w", pady=(8,0))
        canvas = tk.Canvas(self.window, bg=BG, highlightthickness=0)
        scroll = tk.Scrollbar(self.window, command=canvas.yview)
        scroll.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=20)
        canvas.configure(yscrollcommand=scroll.set)
        self.form = tk.Frame(canvas, bg=BG)
        item = canvas.create_window(0, 0, window=self.form, anchor="nw")
        self.form.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(item, width=event.width))
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            canvas.bind(sequence, lambda event: canvas.yview_scroll(
                -1 if getattr(event,"num",0)==4 or getattr(event,"delta",0)>0 else 1, "units"))
        self.row = 0
        self.section("JOYSTICK RESPONSE")
        for label, path, kind in (
            ("Maximum speed · pulses/s", ("joystick", "speed"), float),
            ("Centre dead zone · fraction", ("joystick", "deadzone"), float),
            ("Axes rotation · degrees", ("joystick", "rotation_degrees"), float),
            ("Preset speed · pulses/s", ("motion", "pose_speed"), float),
            ("Calibration jog · pulses/s", ("motion", "jog_speed"), float),
            ("Pose timeout · seconds", ("motion", "timeout_s"), float),
        ):
            self.field(label,path,kind)
        for name,label in (("takeup_gains","Take-up multipliers"),("release_gains","Pay-out multipliers")):
            self.three_fields(label, [("joystick",name,i) for i in range(3)], float)
        self.section("MOTOR DIRECTIONS & TRAVEL")
        self.three_fields("Direction · +1 or -1", [("motors",i,"direction") for i in range(3)], int)
        self.three_fields("Minimum pulse count", [("motors",i,"min_steps") for i in range(3)], int)
        self.three_fields("Maximum pulse count", [("motors",i,"max_steps") for i in range(3)], int)
        self.section("DANCE")
        self.field("Small movement amplitude · pulses", ("dance","amplitude_steps"),int)
        self.field("Dance speed · pulses/s", ("dance","speed"),float)
        self.field("Cycles", ("dance","cycles"),int)
        self.section("TEACH CURL & RELEASE POSES")
        text(self.form,"Use the jog buttons to reach a pose, release them, then Disarm.\n"
             "Record all three counts for each button, or enter the counts directly.",10,MUTED,
             justify="left").grid(row=self.row,column=0,columnspan=4,sticky="w",pady=8)
        self.row+=1
        control = tk.Frame(self.form,bg=BG)
        control.grid(row=self.row,column=0,columnspan=4,sticky="ew",pady=8)
        button(control,"Arm jog",lambda:app.action("arm"),accent=True).pack(side="left",padx=(0,6))
        button(control,"Disarm",lambda:app.action("disarm")).pack(side="left")
        self.row+=1
        for i in range(3):
            text(self.form,f"C{i+1}  ·  hold to jog",10).grid(row=self.row,column=0,sticky="w")
            for column, sign in ((1,1),(2,-1)):
                b = button(self.form,"Take up +" if sign>0 else "Pay out -",lambda:None)
                b.grid(row=self.row,column=column,sticky="ew",padx=4,pady=4)
                b.bind("<ButtonPress-1>",lambda event,index=i,direction=sign:self.jog_start(index,direction))
                b.bind("<ButtonRelease-1>",lambda event:self.jog_stop())
                b.bind("<Leave>",lambda event:self.jog_stop())
            self.row+=1
        for key,label in POSES.items():
            values = app.cfg["poses"][key]
            line = tk.Frame(self.form,bg=PANEL,padx=8,pady=9)
            line.grid(row=self.row,column=0,columnspan=4,sticky="ew",pady=4)
            text(line,label,10,bold=True,width=17,anchor="w").pack(side="left")
            variables = [tk.StringVar(value="" if values is None else str(values[i])) for i in range(3)]
            for variable in variables:
                entry(line,variable,6).pack(side="left",padx=4,ipady=5)
            button(line,"Record current",lambda name=key:self.capture(name)).pack(side="right")
            self.pose_vars[key]=variables
            self.row+=1
        bottom = tk.Frame(self.window,bg=BG,padx=20,pady=16)
        bottom.pack(fill="x")
        text(bottom,"",10,ORANGE,textvariable=self.feedback,wraplength=800,justify="left").pack(anchor="w",pady=(0,10))
        button(bottom,"Apply",lambda:self.apply(False)).pack(side="left",padx=(0,8))
        button(bottom,"Save & apply",lambda:self.apply(True),accent=True).pack(side="left")
        button(bottom,"Close",self.close).pack(side="right")
        self.window.protocol("WM_DELETE_WINDOW",self.close)

    def value(self,path):
        value=self.app.cfg
        for key in path:
            value=value[key]
        return value

    def section(self,label):
        text(self.form,label,10,TEAL,True).grid(row=self.row,column=0,columnspan=4,sticky="w",pady=(20,10))
        self.row+=1

    def field(self,label,path,kind):
        text(self.form,label,10,anchor="w").grid(row=self.row,column=0,sticky="w",pady=6)
        variable=tk.StringVar(value=str(self.value(path)))
        entry(self.form,variable).grid(row=self.row,column=1,columnspan=3,sticky="ew",padx=5,ipady=6)
        self.vars.append((path,variable,kind))
        self.row+=1

    def three_fields(self,label,paths,kind):
        text(self.form,label,10,anchor="w").grid(row=self.row,column=0,sticky="w",pady=6)
        for column,path in enumerate(paths,1):
            variable=tk.StringVar(value=str(self.value(path)))
            entry(self.form,variable).grid(row=self.row,column=column,sticky="ew",padx=5,ipady=6)
            self.vars.append((path,variable,kind))
            self.form.columnconfigure(column,weight=1)
        self.row+=1

    def jog_start(self,index,direction):
        self.app.clear_input()
        self.app.jog=(index,direction)

    def jog_stop(self):
        self.app.jog=None
        self.app.engine.steer((0,0,0))

    def capture(self,name):
        state,_,connected,failed,_=self.app.engine.snapshot()
        if not connected or failed or state.armed or any(state.rates):
            self.feedback.set("Release jog controls and Disarm before recording.")
            return
        if not state.referenced:
            self.feedback.set("Set the neutral reference in the main window first.")
            return
        for variable,value in zip(self.pose_vars[name],state.position):
            variable.set(str(value))
        self.feedback.set(f"Recorded {POSES[name]}. Save & apply to keep this pose.")

    def apply(self,persist):
        self.app.action("disarm")
        candidate=deepcopy(self.app.cfg)
        try:
            for path,variable,kind in self.vars:
                target=candidate
                for key in path[:-1]:
                    target=target[key]
                target[path[-1]]=kind(variable.get())
            for name,variables in self.pose_vars.items():
                values=[v.get().strip() for v in variables]
                candidate["poses"][name]=None if not any(values) else [int(v) for v in values]
            validate(candidate)
            if persist:
                save(self.app.config_path,candidate)
        except (ValueError,KeyError,TypeError,OSError) as exc:
            self.feedback.set(f"Not applied. {exc}")
            return False
        self.app.cfg=candidate
        self.app.engine.request("config",candidate)
        self.app.draw_pad()
        self.feedback.set("Saved and applied." if persist else "Applied for this session. Use Save & apply to keep changes.")
        return True

    def close(self):
        self.app.action("disarm")
        self.app.editor=None
        self.window.destroy()


def main(mode=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("testing","operating"),default=mode)
    parser.add_argument("--sim",action="store_true")
    parser.add_argument("--port")
    parser.add_argument("--direct",action="store_true",help="Skip the launcher")
    args=parser.parse_args()
    config_path=ROOT/"config.json"
    try:
        cfg=load(config_path)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f"Cannot load config.json: {exc}",file=sys.stderr)
        return 1
    root=tk.Tk()
    root.spirob_icon=tk.PhotoImage(file=str(ROOT/"assets/spirob.png"))
    root.iconphoto(True,root.spirob_icon)
    if args.direct:
        selected=(args.mode or "operating",args.sim,args.port or cfg["port"])
    else:
        launcher=Launcher(root,args.mode,args.sim,args.port)
        root.mainloop()
        selected=launcher.result
        if selected is None:
            return 0
        for widget in root.winfo_children():
            widget.destroy()
        for column in (0,1):
            root.columnconfigure(column,weight=0)
        root.rowconfigure(0,weight=0)
    selected_mode,simulation,port=selected
    cfg["port"]=port
    if simulation:
        config_path=ROOT/"config.simulation.json"
        if config_path.exists():
            try:
                cfg=load(config_path)
            except (OSError,ValueError,KeyError,TypeError) as exc:
                messagebox.showerror("Simulation settings",str(exc),parent=root)
                root.destroy()
                return 1
        cfg=demo_config(cfg)
    app=Workspace(root,cfg,config_path,selected_mode,simulation)
    try:
        root.mainloop()
    finally:
        if not app.closed:
            app.close()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
