import copy
import tempfile
import json
import unittest
from pathlib import Path
from motion import load_config, manual_vector, JogPlanner, action
from transport import SimLink, parse_state
from controller import Controller

BASE = Path(__file__).resolve().parents[1]

class Clock:
    def __init__(self): self.now = 0
    def __call__(self): return self.now
    def advance(self, seconds): self.now += seconds

class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.cfg = load_config(BASE / 'config.json')
        self.clock = Clock()
        self.link = SimLink(self.clock)
        self.c = Controller(self.link, self.cfg, clock=self.clock)
        self.c.zero()
        self.c.arm()

    def run_for(self, seconds):
        for _ in range(round(seconds / .05)):
            self.clock.advance(.05)
            self.c.tick()

    def test_independent_and_opposite_keys(self):
        self.assertEqual(manual_vector({'r', 'n'}, .25), (1, -1))
        self.assertEqual(manual_vector({'r', 'e', 'm'}, .25), (0, 1))
        self.assertEqual(manual_vector({'Left'}, .25), (1, -.25))
        self.assertEqual(manual_vector({'Right'}, .25), (-.25, 1))
        self.assertEqual(manual_vector({'Left', 'Right'}, .25), (0, 0))

    def test_fractional_A_conserved(self):
        planner = JogPlanner()
        p = (0, 0)
        for _ in range(20): p, _ = planner.next(p, (1, -.25), self.cfg)
        self.assertEqual(p, (300, -75))

    def test_limit_rejects_pair(self):
        with self.assertRaises(ValueError):
            JogPlanner().next((555, 0), (1, -.25), self.cfg)
        with self.assertRaises(RuntimeError): self.link.request('MOVE 561 0 100')
        self.assertEqual(self.link.s.position, (0, 0))

    def test_curl_absolute_repeat_and_counts(self):
        self.c.start_action('j')
        self.run_for(4)
        self.assertEqual(self.c.state.position, (200, -50))
        self.c.start_action('j')
        self.run_for(1)
        self.assertEqual(self.c.state.position, (200, -50))

    def test_stop_mid_motion_and_cancel(self):
        self.c.start_action('1')
        self.run_for(.4)
        p = self.c.stop().position
        self.assertNotEqual(p, (0, 0))
        self.run_for(2)
        self.assertEqual(self.c.state.position, p)
        self.assertFalse(self.c.queue)

    def test_watchdog_requires_rearm(self):
        self.c.send('MOVE 300 0 100')
        self.clock.advance(1)
        s = self.c.send('STATE')
        self.assertEqual(s.p1, 50)
        self.assertFalse(s.armed)
        self.assertFalse(s.busy)
        with self.assertRaises(RuntimeError): self.c.send('MOVE 0 0 100')

    def test_manual_release(self):
        self.c.manual({'r', 'm'})
        self.run_for(.2)
        self.c.manual(set())
        p = self.c.state.position
        self.run_for(1)
        self.assertEqual(self.c.state.position, p)

    def test_all_presets_complete_at_zero(self):
        for key in ('1', '2', '3'):
            self.c.start_action(key)
            self.run_for(30)
            self.assertEqual(self.c.mode, 'idle')
            self.assertEqual(self.c.state.position, (0, 0))

    def test_dwell(self):
        self.c.start_action('3')
        self.run_for(.4)
        self.assertEqual(self.c.state.position, (30, 30))
        self.run_for(.2)
        self.assertEqual(self.c.state.position, (30, 30))
        self.run_for(.6)
        self.assertNotEqual(self.c.state.position, (30, 30))

    def test_reference_rules(self):
        with self.assertRaises(ValueError): self.c.zero()
        other = Controller(SimLink(self.clock), self.cfg, clock=self.clock)
        with self.assertRaises(ValueError): other.arm()

    def test_validation_rejects_bad_config(self):
        for mutate in [lambda c: c.update(A=float('nan')),
                       lambda c: c.update(curl_left_target=[561, 0]),
                       lambda c: c.update(jog_speed=0),
                       lambda c: c.update(motor_signs=[0, 1])]:
            c = copy.deepcopy(self.cfg)
            mutate(c)
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / 'bad.json'
                p.write_text(json.dumps(c))
                with self.assertRaises(ValueError): load_config(p)

    def test_parse_rejects_wrong_firmware(self):
        with self.assertRaises(RuntimeError): parse_state('OK MOVE1')
        with self.assertRaises(RuntimeError): parse_state('STATE 0 0 7 0 1')
        self.assertEqual(parse_state('STATE -25 100 0 1 1').position, (-25, 100))

if __name__ == '__main__': unittest.main()
