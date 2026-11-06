"""Shared logical motion definitions. No GUI, camera, or serial dependencies."""
import json
import math
from pathlib import Path


def integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name}: expected integer in [{low}, {high}]')


def check_target(target, cfg):
    if not isinstance(target, (list, tuple)) or len(target) != 2:
        raise ValueError('Each target must contain two integer pulse counts')
    for i, value in enumerate(target):
        integer(value, f'motor {i+1} target', *cfg['limits'][i])
    return tuple(target)


def load_config(path):
    c = json.loads(Path(path).read_text(encoding='utf-8'))
    for name in ('motor_signs', 'steps_per_revolution', 'limits'):
        if len(c[name]) != 2:
            raise ValueError(f'{name} must have two entries')
    for sign in c['motor_signs']:
        if type(sign) is not int or sign not in (-1, 1):
            raise ValueError('motor_signs must be +1 or -1')
    for spr in c['steps_per_revolution']:
        integer(spr, 'steps_per_revolution', 1, 1000000)
    for pair in c['limits']:
        if len(pair) != 2:
            raise ValueError('limits must be [min,max] pairs')
        integer(pair[0], 'lower limit', -20000, -1)
        integer(pair[1], 'upper limit', 1, 20000)
    for name in ('jog_speed', 'curl_speed', 'preset_speed'):
        integer(c[name], name, 1, 1000)
    integer(c['jog_segment_steps'], 'jog_segment_steps', 1, 100)
    if type(c['A']) not in (float, int) or not math.isfinite(c['A']) or not 0 <= c['A'] <= 2:
        raise ValueError('A must be finite, between 0 and 2')
    if c['jog_speed'] * max(1, c['A']) > 1000:
        raise ValueError('A × jog_speed exceeds 1000 pulses/s')
    for key in ('curl_left_target', 'curl_right_target'):
        check_target(c[key], c)
    if set(c['presets']) != {'1', '2', '3'}:
        raise ValueError('Provide exactly presets 1, 2, 3')
    for p in c['presets'].values():
        if not isinstance(p['name'], str):
            raise ValueError('Preset name must be text')
        integer(p['repeat'], 'repeat', 1, 100)
        integer(p['dwell_ms'], 'dwell_ms', 0, 60000)
        if not 1 <= len(p['waypoints']) <= 100:
            raise ValueError('Provide 1..100 waypoints')
        for point in p['waypoints']:
            check_target(point, c)
    return c


def manual_vector(keys, a):
    """Arrows override motor keys; opposite arrows cancel. + means tighten."""
    if 'Left' in keys or 'Right' in keys:
        if 'Left' in keys and 'Right' in keys:
            return (0, 0)
        return (1, -a) if 'Left' in keys else (-a, 1)
    return (int('r' in keys) - int('e' in keys),
            int('m' in keys) - int('n' in keys))


class JogPlanner:
    """Carry fractional steps across segments so noninteger A does not drift."""
    def __init__(self):
        self.vector = None
        self.remainder = [0.0, 0.0]

    def next(self, position, vector, cfg):
        if vector != self.vector:
            self.vector = vector
            self.remainder = [0.0, 0.0]
        delta = []
        for i in range(2):
            value = vector[i] * cfg['jog_segment_steps'] + self.remainder[i]
            whole = math.trunc(value)
            self.remainder[i] = value - whole
            delta.append(whole)
        target = tuple(position[i] + delta[i] for i in range(2))
        check_target(target, cfg)  # reject whole pair; never clip only one cable
        # Rate is the faster axis; preserves leader speed even for A > 1.
        speed = math.ceil(cfg['jog_speed'] * max(1, *(abs(v) for v in vector)))
        if speed > 1000:
            raise ValueError('A × jog_speed exceeds the firmware rate limit')
        return target, speed


def action(key, cfg):
    """Absolute logical positions relative to the manually established zero."""
    if key in ('j', 'l'):
        field = 'curl_left_target' if key == 'j' else 'curl_right_target'
        return [(tuple(cfg[field]), cfg['curl_speed'], 0)]
    if key == 'h':
        return [((0, 0), cfg['curl_speed'], 0)]
    p = cfg['presets'][key]
    return [(tuple(t), cfg['preset_speed'], p['dwell_ms'] / 1000)
            for _ in range(p['repeat']) for t in p['waypoints']]
