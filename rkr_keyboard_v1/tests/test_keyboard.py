"""Headless handler tests; not rendered desktop GUI validation."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from keyboard_control import Application

class KeyboardTests(unittest.TestCase):
    def setUp(self):
        self.app = Application.__new__(Application)
        self.app.root = Mock()
        self.app.control = Mock()
        self.app.control.mode = 'manual'
        self.app.notice = Mock()
        self.app.failed = False
        self.app.closing = False
        self.app.stop_latch = False
        self.app.pressed = set()
        self.app.releases = {}

    def press(self, key):
        self.app.on_press(SimpleNamespace(keysym=key))

    def test_oneshot_repeat_ignored(self):
        self.press('j'); self.press('j'); self.press('j')
        self.app.control.start_action.assert_called_once_with('j')

    def test_stop_latched_until_every_key_released(self):
        self.press('r'); self.press('space'); self.press('m'); self.press('1')
        self.app.control.start_action.assert_not_called()
        self.assertEqual(self.app.control.manual.call_count, 1)
        self.app.control.mode = 'idle'
        for key in ('r', 'space', 'm', '1'): self.app.finish_release(key)
        self.assertFalse(self.app.stop_latch)
        self.press('m')
        self.app.control.manual.assert_called_with({'m'})

    def test_release_preserves_other_motor(self):
        self.press('r'); self.press('m')
        self.app.finish_release('r')
        self.app.control.manual.assert_called_with({'m'})

    def test_focus_loss_clears_keys_and_disarms(self):
        self.press('r')
        self.app.focus_lost(None)
        self.assertFalse(self.app.pressed)
        self.app.control.stop.assert_called_with(disarm=True)

if __name__ == '__main__': unittest.main()
