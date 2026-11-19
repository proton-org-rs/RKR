"""Only this thread touches the serial link. UI freezes expire movement intent."""
from collections import deque
from copy import deepcopy
import threading
import time

from settings import dance_targets, validate, validate_target
from transport import State, SerialLink, SimLink, FAULTS

TICK = 0.05
UI_TIMEOUT = 0.25


class Engine(threading.Thread):
    def __init__(self, cfg, simulation=False, link_factory=None, clock=time.monotonic):
        super().__init__(daemon=True, name="RKR motion")
        self.cfg = deepcopy(cfg)
        self.simulation = simulation
        self.link_factory = link_factory
        self.clock = clock
        self.lock = threading.Lock()
        self.shutdown = threading.Event()
        self.commands = deque()
        self.state = State()
        self.message = "Connecting to controller…"
        self.connected = False
        self.failed = False
        self.action = "Hold"
        self.manual = (0, 0, 0)
        self.ui_contact = clock()
        self.last_command = ""
        self.targets = deque()
        self.target_speed = cfg["motion"]["pose_speed"]
        self.deadline = 0
        self.intent_blocked = False

    def snapshot(self):
        with self.lock:
            return self.state, self.message, self.connected, self.failed, self.action

    def heartbeat(self):
        with self.lock:
            self.ui_contact = self.clock()

    def steer(self, rates):
        with self.lock:
            rates = tuple(rates)
            if rates != self.manual and any(rates):
                self.intent_blocked = False
                self.commands.append(("manual", rates))
            self.manual = rates

    def request(self, operation, value=None):
        with self.lock:
            if operation in ("stop", "disarm", "zero", "config"):
                self.commands.clear()
                self.manual = (0, 0, 0)
                self.intent_blocked = True
            self.commands.append((operation, deepcopy(value)))

    def publish(self, **values):
        with self.lock:
            for name, value in values.items():
                setattr(self, name, value)

    def send(self, operation):
        self.last_command = operation
        try:
            result = self.link.request(operation)
        except RuntimeError as exc:
            # A limit or watchdog can disarm between STATE and the next V packet.
            if not operation.startswith("V ") or "COMMAND_OR_STATE" not in str(exc):
                raise
            result = self.link.request("STATE")
            if result.armed or not result.referenced or result.fault not in (1, 2, 3, 4, 5):
                raise
            self.cancel()
            self.publish(intent_blocked=True, message="Controller stopped · release controls and re-arm")
        self.publish(state=result)
        return result

    def configure(self, cfg):
        validate(cfg)
        self.send("DISARM")
        args = [m["direction"] for m in cfg["motors"]]
        args += [v for m in cfg["motors"] for v in (m["min_steps"], m["max_steps"])]
        self.send("CONFIG " + " ".join(map(str, args)))
        self.cfg = deepcopy(cfg)

    def cancel(self):
        self.targets.clear()
        self.publish(action="Hold")

    def start_targets(self, targets, speed, label):
        if not self.state.armed:
            raise ValueError("Establish the reference and press Arm first.")
        for target in targets:
            validate_target(target, self.cfg)
        self.send("STOP")
        self.targets = deque(tuple(t) for t in targets)
        self.target_speed = speed
        self.deadline = self.clock() + self.cfg["motion"]["timeout_s"]
        self.publish(action=label, message=f"{label} · Stop cancels immediately")

    def handle(self, operation, value):
        if operation in ("stop", "disarm", "zero", "config"):
            self.cancel()
        if operation == "stop":
            self.send("STOP")
            self.publish(message="Stopped at current pose")
        elif operation == "disarm":
            self.send("DISARM")
            self.publish(message="Disarmed · motor holding outputs retained")
        elif operation == "zero":
            if self.state.armed:
                raise ValueError("Disarm before setting the reference.")
            self.send("ZERO")
            self.publish(message="Reference set · press Arm")
        elif operation == "arm":
            if not self.state.referenced:
                raise ValueError("Set the reference in the physical neutral pose first.")
            if not self.state.armed:
                self.send("ARM")
            self.publish(message="Ready · hold and drag the joystick")
        elif operation == "manual":
            self.cancel()
        elif operation == "home":
            self.start_targets([(0, 0, 0)], self.cfg["motion"]["pose_speed"], "Return to reference")
        elif operation == "pose":
            target = self.cfg["poses"][value]
            if target is None:
                raise ValueError("Teach this pose in Testing before using it on hardware.")
            self.start_targets([target], self.cfg["motion"]["pose_speed"], value.replace("_", " ").title())
        elif operation == "dance":
            self.start_targets(dance_targets(self.state.position, self.cfg), self.cfg["dance"]["speed"], "Dance")
        elif operation == "config":
            hardware_changed = self.cfg["motors"] != value["motors"]
            if hardware_changed:
                self.configure(value)
                self.publish(message="Hardware settings changed · set the reference again")
            else:
                self.send("DISARM")
                self.cfg = deepcopy(value)
                self.publish(message="Parameters applied · press Arm")

    def cycle(self):
        with self.lock:
            commands = list(self.commands)
            self.commands.clear()
            manual = self.manual
            contact = self.ui_contact
            blocked = self.intent_blocked
        for operation, value in commands:
            try:
                self.handle(operation, value)
            except ValueError as exc:
                self.cancel()
                self.send("STOP")
                self.publish(message=str(exc))
        state = self.send("STATE")
        if not state.armed:
            self.cancel()
            if state.fault:
                self.publish(message=FAULTS[state.fault] + " · release controls, then re-arm",
                             intent_blocked=True)
            return
        if self.clock() - contact > UI_TIMEOUT:
            self.cancel()
            self.send("DISARM")
            self.publish(message="Interface paused · motion disarmed", intent_blocked=True)
            return
        if self.targets:
            if self.clock() >= self.deadline:
                self.cancel()
                self.send("DISARM")
                self.publish(message="Pose timed out · check speed, limits and calibration")
                return
            target = self.targets[0]
            error = tuple(t-p for t, p in zip(target, state.position))
            if not any(error):
                self.send("STOP")
                self.targets.popleft()
                self.deadline = self.clock() + self.cfg["motion"]["timeout_s"]
                if not self.targets:
                    self.publish(action="Hold", message="Pose reached")
                return
            # Slow on approach. Dance uses a shorter settling horizon for quick gestures.
            distance = max(abs(v) for v in error)
            approach = 10 if self.action == "Dance" else 5
            rate = min(self.target_speed, max(5, distance*approach))
            rates = tuple(round(v/distance*rate*1000) for v in error)
        else:
            rates = (0, 0, 0) if blocked else manual
        result = self.send("V " + " ".join(map(str, rates)))
        if not result.armed:
            self.cancel()
            self.publish(message=FAULTS.get(result.fault, "Stopped"), intent_blocked=True)

    def run(self):
        self.link = None
        try:
            self.link = self.link_factory() if self.link_factory else (
                SimLink() if self.simulation else SerialLink(self.cfg["port"]))
            self.configure(self.cfg)
            self.publish(connected=True, message="Connected · set the neutral reference")
            while not self.shutdown.is_set():
                started = self.clock()
                self.cycle()
                self.shutdown.wait(max(0, TICK-(self.clock()-started)))
        except Exception as exc:
            self.publish(failed=True, connected=False, action="Fault",
                         message=f"{self.last_command or 'Connect'} · {type(exc).__name__} · {exc}")
        finally:
            if self.link is not None:
                try:
                    self.link.request("DISARM")
                except Exception:
                    pass
                self.link.close()

    def close(self):
        self.shutdown.set()
