"""Protocol and explicit simulation. Serial failures never switch to simulation."""
from dataclasses import dataclass
import time


@dataclass
class State:
    p1: int = 0
    p2: int = 0
    busy: bool = False
    armed: bool = False
    referenced: bool = False

    @property
    def position(self):
        return (self.p1, self.p2)


def parse_state(line):
    parts = line.split()
    if len(parts) != 6 or parts[0] != 'STATE':
        raise RuntimeError(f'Unexpected firmware response: {line}')
    values = [int(p) for p in parts[1:]]
    if any(v not in (0, 1) for v in values[2:]):
        raise RuntimeError('Invalid status flags')
    return State(*values[:2], *(bool(v) for v in values[2:]))


class SerialLink:
    def __init__(self, port):
        import serial
        self.serial = serial.Serial(port, 115200, timeout=0.02, write_timeout=0.2)
        try:
            time.sleep(2)  # boards that reset when serial opens
            self.serial.reset_input_buffer()
            self.serial.write(b'HELLO\n')
            line = self.serial.readline().decode('ascii').strip()
            if line != 'RKR 1':
                raise RuntimeError('Upload firmware/rkr_controller first (RKR protocol 1 required)')
        except Exception:
            self.serial.close()
            raise

    def request(self, cmd):
        self.serial.write((cmd + '\n').encode('ascii'))
        deadline = time.monotonic() + 0.3
        data = bytearray()
        while time.monotonic() < deadline:
            data.extend(self.serial.read(1))
            if len(data) > 120:
                raise RuntimeError('Oversized serial response')
            if data.endswith(b'\n'):
                return parse_state(data.decode('ascii').strip())
        raise TimeoutError('No acknowledgement: controller disconnected or stalled')

    def close(self):
        self.serial.close()


class SimLink:
    """Timing/position simulator, not a model of cable tension or motor dynamics."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.s = State()
        self.configured = False
        self.last = clock()
        self.start = clock()
        self.origin = (0, 0)
        self.target = (0, 0)
        self.rate = 100
        self.limits = ((-560, 560), (-560, 560))

    def advance(self):
        now = self.clock()
        end = min(now, self.last + 0.5) if self.s.armed else now
        if self.s.busy:
            delta = [self.target[i] - self.origin[i] for i in range(2)]
            total = max(abs(d) for d in delta)
            ticks = min(total, int(max(0, end - self.start) * self.rate))
            values = [self.origin[i] + (1 if delta[i] >= 0 else -1) *
                      (ticks * abs(delta[i]) // total) for i in range(2)]
            self.s.p1, self.s.p2 = values
            self.s.busy = ticks < total
        if self.s.armed and now - self.last > 0.5:
            self.s.busy = self.s.armed = False

    def request(self, cmd):
        self.advance()
        parts = cmd.split()
        op = parts[0]
        args = [int(x) for x in parts[1:]]
        s = self.s
        if op == 'INIT' and len(args) == 6 and not s.busy and not s.armed:
            self.limits = ((args[2], args[3]), (args[4], args[5]))
            self.configured = True
            s.referenced = False
        elif op == 'ZERO' and not args and self.configured and not s.armed and not s.busy:
            s.p1 = s.p2 = 0
            s.referenced = True
        elif op == 'ARM' and not args and self.configured and s.referenced and not s.busy:
            s.armed = True
            self.last = self.clock()
        elif op in ('STOP', 'DISARM') and not args:
            s.busy = False
            if op == 'DISARM':
                s.armed = False
        elif op == 'STATE' and not args:
            self.last = self.clock()
        elif op == 'MOVE' and len(args) == 3 and s.armed and s.referenced and not s.busy:
            if not all(self.limits[i][0] <= args[i] <= self.limits[i][1] for i in range(2)) or not 1 <= args[2] <= 1000:
                raise RuntimeError('ERR range')
            self.origin = s.position
            self.target = tuple(args[:2])
            self.rate = args[2]
            self.start = self.last = self.clock()
            s.busy = self.origin != self.target
        else:
            raise RuntimeError('ERR command_or_state')
        return State(s.p1, s.p2, s.busy, s.armed, s.referenced)

    def close(self):
        pass
