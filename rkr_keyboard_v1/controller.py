"""Reusable controller for keyboard now, gestures later. One motion owner at a time."""
from collections import deque
import time
from motion import JogPlanner, action, manual_vector, check_target


class Controller:
    def __init__(self, link, cfg, log=lambda *args: None, clock=time.monotonic):
        self.link, self.cfg, self.log, self.clock = link, cfg, log, clock
        self.queue = deque()
        self.keys = set()
        self.jog = JogPlanner()
        self.mode = 'idle'
        self.wait_until = 0
        self.dwell = 0
        self.state = self.send('DISARM')
        signs = cfg['motor_signs']
        limits = cfg['limits']
        self.state = self.send(f'INIT {signs[0]} {signs[1]} {limits[0][0]} {limits[0][1]} {limits[1][0]} {limits[1][1]}')

    def send(self, cmd):
        s = self.link.request(cmd)
        self.state = s
        self.log(cmd, s)
        return s

    def stop(self, disarm=False):
        self.queue.clear()
        self.keys.clear()
        self.mode = 'idle'
        self.wait_until = self.dwell = 0
        self.jog = JogPlanner()
        return self.send('DISARM' if disarm else 'STOP')

    def zero(self):
        if self.state.busy or self.state.armed:
            raise ValueError('Disarm with Escape before establishing zero')
        return self.send('ZERO')

    def arm(self):
        if not self.state.referenced:
            raise ValueError('Establish a physical reference with Z first')
        self.stop()
        return self.send('ARM')

    def manual(self, keys):
        self.stop()
        if not self.state.armed:
            return
        self.keys = set(keys)
        self.mode = 'manual'

    def start_action(self, key):
        if not self.state.armed:
            raise ValueError('Press Enter to arm first')
        self.stop()
        self.queue.extend(action(key, self.cfg))
        self.mode = 'sequence'

    def tick(self):
        s = self.send('STATE')  # authoritative emitted-pulse positions + heartbeat
        if not s.armed:
            self.queue.clear()
            self.keys.clear()
            self.mode = 'idle'
            return
        if s.busy:
            return
        if self.mode == 'manual':
            vector = manual_vector(self.keys, self.cfg['A'])
            if vector == (0, 0):
                return
            try:
                target, speed = self.jog.next(s.position, vector, self.cfg)
            except ValueError:
                self.stop()
                raise
            self.send(f'MOVE {target[0]} {target[1]} {speed}')
        elif self.mode == 'sequence':
            if self.dwell:
                self.wait_until = self.clock() + self.dwell
                self.dwell = 0
            if self.clock() < self.wait_until:
                return
            if not self.queue:
                self.mode = 'idle'
                return
            target, speed, self.dwell = self.queue.popleft()
            check_target(target, self.cfg)
            self.send(f'MOVE {target[0]} {target[1]} {speed}')
