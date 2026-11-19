"""Validated persistent settings, joystick mixing and taught robot poses."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile

AXES = ((0.0, 1.0), (math.sqrt(3)/2, -0.5), (-math.sqrt(3)/2, -0.5))
POSES = {
    "curl_1": "Curl C1", "curl_2": "Curl C2", "curl_3": "Curl C3",
    "curl_12": "Curl C1 + C2", "curl_23": "Curl C2 + C3", "curl_31": "Curl C3 + C1",
    "release": "Release all",
}
DEFAULT = {
    "version": 2, "port": "/dev/ttyUSB0",
    "motors": [
        {"name": "Cable 1", "direction": 1, "min_steps": -560, "max_steps": 560},
        {"name": "Cable 2", "direction": 1, "min_steps": -560, "max_steps": 560},
        {"name": "Cable 3", "direction": 1, "min_steps": -560, "max_steps": 560},
    ],
    "joystick": {"speed": 150, "deadzone": 0.08, "rotation_degrees": 0,
                 "takeup_gains": [1.0, 1.0, 1.0], "release_gains": [1.0, 1.0, 1.0]},
    "motion": {"pose_speed": 150, "jog_speed": 80, "timeout_s": 45},
    "dance": {"amplitude_steps": 12, "speed": 220, "cycles": 2},
    "poses": {name: None for name in POSES},
}


def numeric(value, label, low, high, integer=False):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be between {low} and {high}.")
    if integer and type(value) is not int:
        raise ValueError(f"{label} must be a whole number.")


def validate(cfg):
    if type(cfg) is not dict or type(cfg.get("version")) is not int or cfg["version"] != 2:
        raise ValueError("Use the joystick version 2 configuration.")
    if not isinstance(cfg.get("port"), str) or not cfg["port"].strip():
        raise ValueError("Enter a serial port.")
    if not isinstance(cfg.get("motors"), list) or len(cfg["motors"]) != 3:
        raise ValueError("Exactly three motor entries are required.")
    for i, motor in enumerate(cfg["motors"]):
        if not isinstance(motor.get("name"), str) or not motor["name"]:
            raise ValueError("Each cable needs a name.")
        if type(motor.get("direction")) is not int or motor["direction"] not in (-1, 1):
            raise ValueError("Direction must be +1 or -1.")
        numeric(motor["min_steps"], f"C{i+1} minimum", -20000, -1, True)
        numeric(motor["max_steps"], f"C{i+1} maximum", 1, 20000, True)
    joy = cfg["joystick"]
    numeric(joy["speed"], "Joystick speed", 1, 1000)
    numeric(joy["deadzone"], "Dead zone", 0, 0.35)
    numeric(joy["rotation_degrees"], "Axis rotation", -180, 180)
    for name in ("takeup_gains", "release_gains"):
        if not isinstance(joy[name], list) or len(joy[name]) != 3:
            raise ValueError(f"{name} needs three values.")
        for gain in joy[name]:
            numeric(gain, name, 0.01, 5)
            if gain * joy["speed"] > 1000:
                raise ValueError("Joystick speed × every gain must be at most 1000 pulses/s.")
    numeric(cfg["motion"]["pose_speed"], "Pose speed", 1, 1000)
    numeric(cfg["motion"]["jog_speed"], "Individual jog speed", 1, 1000)
    numeric(cfg["motion"]["timeout_s"], "Pose timeout", 1, 600)
    numeric(cfg["dance"]["amplitude_steps"], "Dance amplitude", 1, 200, True)
    numeric(cfg["dance"]["speed"], "Dance speed", 1, 1000)
    numeric(cfg["dance"]["cycles"], "Dance cycles", 1, 10, True)
    if set(cfg["poses"]) != set(POSES):
        raise ValueError("Configuration must include all seven taught poses.")
    for label, target in cfg["poses"].items():
        if target is not None:
            validate_target(target, cfg, label)
    return cfg


def validate_target(target, cfg, label="Pose"):
    if not isinstance(target, (list, tuple)) or len(target) != 3:
        raise ValueError(f"{label} needs three pulse positions.")
    for i, value in enumerate(target):
        motor = cfg["motors"][i]
        numeric(value, f"{label} C{i+1}", motor["min_steps"], motor["max_steps"], True)


def load(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save(path, cfg):
    validate(cfg)
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(cfg, handle, indent=2, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def joystick_rates(x, y, cfg):
    """Screen-independent coordinates: +x right, +y up. Positive takes up cable."""
    length = math.hypot(x, y)
    if length <= cfg["joystick"]["deadzone"]:
        return (0, 0, 0)
    radius = min(1.0, length)
    scale = (radius - cfg["joystick"]["deadzone"]) / (1 - cfg["joystick"]["deadzone"])
    rotation = math.radians(cfg["joystick"]["rotation_degrees"])
    x, y = (x*math.cos(rotation)+y*math.sin(rotation))/length, (-x*math.sin(rotation)+y*math.cos(rotation))/length
    rates = []
    for i, (axis_x, axis_y) in enumerate(AXES):
        projection = x*axis_x + y*axis_y
        gains = cfg["joystick"]["takeup_gains"] if projection >= 0 else cfg["joystick"]["release_gains"]
        rates.append(round(projection * scale * cfg["joystick"]["speed"] * gains[i] * 1000))
    return tuple(rates)


def dance_targets(origin, cfg):
    amplitude = cfg["dance"]["amplitude_steps"]
    points = []
    # Integer zero-sum offsets, then a deliberate return to the starting pose.
    patterns = ((2, -1, -1), (-1, 2, -1), (-1, -1, 2), (-2, 1, 1), (1, -2, 1), (1, 1, -2))
    half = max(1, amplitude // 2)
    for _ in range(cfg["dance"]["cycles"]):
        for pattern in patterns:
            target = tuple(origin[i] + pattern[i]*half for i in range(3))
            validate_target(target, cfg, "Dance")
            points.append(target)
    points.append(tuple(origin))
    return points


def demo_config(cfg):
    cfg = copy.deepcopy(cfg)
    # Demo values stay inside configured travel limits, only in explicit simulation.
    for key in POSES:
        if cfg["poses"][key] is not None:
            continue
        selected = {int(c)-1 for c in key.replace("curl_", "")} if key.startswith("curl_") else set()
        cfg["poses"][key] = [
            min(120, m["max_steps"]) if i in selected else max(-60, m["min_steps"])
            for i, m in enumerate(cfg["motors"])
        ]
    return cfg
