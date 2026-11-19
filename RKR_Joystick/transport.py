"""Matched RKR3 protocol 1 serial transport and explicit simulation."""
import os
import time
from dataclasses import dataclass
MAX_RATE = 1000
WATCHDOG_SECONDS = 0.4
FAULTS = {0:"", 1:"Watchdog timeout", 2:"Cable 1 limit", 3:"Cable 2 limit", 4:"Cable 3 limit", 5:"Invalid controller command"}

@dataclass(frozen=True)
class State:
    position: tuple = (0, 0, 0)
    armed: bool = False
    referenced: bool = False
    fault: int = 0
    rates: tuple = (0, 0, 0)


def parse_state(payload):
    parts = payload.split()
    if len(parts) != 10 or parts[0] != 'STATE':
        raise RuntimeError(f'Unexpected controller response: {payload}')
    values = [int(value) for value in parts[1:]]
    if values[3] not in (0, 1) or values[4] not in (0, 1) or values[5] not in FAULTS:
        raise RuntimeError('Invalid controller status flags')
    if any(abs(p) > 20000 for p in values[:3]) or any(abs(r) > MAX_RATE * 1000 for r in values[6:]):
        raise RuntimeError('Invalid controller position or rate')
    return State(tuple(values[:3]), bool(values[3]), bool(values[4]), values[5], tuple(values[6:]))


class SerialLink:
    def __init__(self, port):
        import serial
        options = {'exclusive': True} if os.name == 'posix' else {}
        self.serial = serial.Serial(port, 115200, timeout=0.01, write_timeout=0.15, **options)
        self.sequence = 0
        self.recent_lines = []
        try:
            # Match the standalone diagnostic: leave the board quiet during startup.
            time.sleep(3)
            deadline = time.monotonic() + 6
            while time.monotonic() < deadline:
                try:
                    reply = self.exchange('HELLO', timeout=0.5, handshake=True)
                    if reply == 'RKR3 1':
                        break
                except TimeoutError:
                    continue
                raise RuntimeError(f'Expected RKR3 1 on {port}; received {reply!r}. '
                                   'Upload firmware/rkr_3cable/rkr_3cable.ino.')
            else:
                raise RuntimeError(f'No RKR3 handshake on {port} at 115200 baud. '
                                   f'Received lines: {self.recent_lines!r}')
        except Exception:
            self.serial.close()
            raise

    def exchange(self, command, timeout=0.2, handshake=False):
        self.sequence = self.sequence % 1000000 + 1
        packet = f'{self.sequence} {command}\n'.encode('ascii')
        if self.serial.write(packet) != len(packet):
            raise RuntimeError('Incomplete serial write')
        deadline = time.monotonic() + timeout
        data = bytearray()
        while time.monotonic() < deadline:
            data.extend(self.serial.read(1))
            if len(data) > 256:
                raise RuntimeError('Oversized serial response')
            if not data.endswith(b'\n'):
                continue
            line = data.decode('ascii', errors='replace').strip()
            data.clear()
            self.recent_lines.append(line)
            self.recent_lines = self.recent_lines[-6:]
            prefix, separator, payload = line.partition(' ')
            if prefix != str(self.sequence) or not separator:
                if handshake:
                    continue
                raise RuntimeError(f'Unexpected reply to {command!r}: {line!r}. '
                                   'Reconnect and set zero.')
            if payload.startswith('ERR '):
                raise RuntimeError(f'Controller rejected {command!r}: {payload[4:]}')
            return payload
        raise TimeoutError(f'Controller response timed out for {command!r}. '
                           f'Received lines: {self.recent_lines!r}; partial bytes: {bytes(data)!r}')

    def request(self, command):
        return parse_state(self.exchange(command))

    def close(self):
        self.serial.close()


class SimLink:
    """Pulse-position simulator with the same command vocabulary and watchdog."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.position = [0, 0, 0]
        self.rates = [0, 0, 0]
        self.next_step = [0.0, 0.0, 0.0]
        self.armed = self.referenced = self.configured = False
        self.fault = 0
        self.last_contact = clock()
        self.limits = [(-560, 560)] * 3

    def stop(self, disarm=False, fault=None):
        self.rates = [0, 0, 0]
        if disarm:
            self.armed = False
        if fault is not None:
            self.fault = fault

    def advance(self):
        now = self.clock()
        end = min(now, self.last_contact + WATCHDOG_SECONDS)
        while self.armed and any(self.rates):
            event = min(self.next_step[i] for i in range(3) if self.rates[i])
            if event > end:
                break
            due = [i for i in range(3) if self.rates[i] and self.next_step[i] <= event]
            for i in due:
                step = 1 if self.rates[i] > 0 else -1
                if not self.limits[i][0] <= self.position[i] + step <= self.limits[i][1]:
                    self.stop(disarm=True, fault=i + 2)
                    break
            if not self.armed:
                break
            for i in due:
                self.position[i] += 1 if self.rates[i] > 0 else -1
                self.next_step[i] += 1000 / abs(self.rates[i])
        if self.armed and now - self.last_contact >= WATCHDOG_SECONDS:
            self.stop(disarm=True, fault=1)

    def request(self, command):
        self.advance()
        parts = command.split()
        operation, args = parts[0], [int(value) for value in parts[1:]]
        now = self.clock()
        if operation == 'CONFIG' and len(args) == 9 and not self.armed:
            if any(value not in (-1, 1) for value in args[:3]):
                raise RuntimeError('Invalid direction')
            limits = [(args[i], args[i + 1]) for i in (3, 5, 7)]
            if any(not -20000 <= low < 0 < high <= 20000 for low, high in limits):
                raise RuntimeError('Invalid limits')
            self.stop(fault=0)
            self.limits = limits
            self.configured, self.referenced = True, False
        elif operation == 'ZERO' and not args and self.configured and not self.armed:
            self.position = [0, 0, 0]
            self.referenced, self.fault = True, 0
        elif operation == 'ARM' and not args and self.configured and self.referenced and not self.armed:
            self.stop(fault=0)
            self.armed, self.last_contact = True, now
        elif operation == 'V' and len(args) == 3 and self.armed:
            if any(abs(value) > MAX_RATE * 1000 for value in args):
                self.stop(disarm=True, fault=5)
                raise RuntimeError('Invalid velocity')
            for i, rate in enumerate(args):
                if rate and rate != self.rates[i]:
                    self.next_step[i] = now + 1000 / abs(rate)
            self.rates, self.last_contact = args, now
        elif operation == 'STOP' and not args:
            self.stop()
            self.last_contact = now
        elif operation == 'DISARM' and not args:
            self.stop(disarm=True)
        elif operation != 'STATE' or args:
            self.stop(disarm=True, fault=5)
            raise RuntimeError('Command is not valid in this state')
        return State(tuple(self.position), self.armed, self.referenced, self.fault, tuple(self.rates))

    def close(self):
        pass

