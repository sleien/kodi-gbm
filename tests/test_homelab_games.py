"""Tests for waking the gaming PC until Sunshine answers."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addons",
                                "script.homelab.games", "resources", "lib"))

import homelab_games  # noqa: E402


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class WaitTests(unittest.TestCase):
    def run_wait(self, up_after=None, cancel_after=None, **kw):
        clock = Clock()
        wakes = []
        result = homelab_games.wait_until_up(
            "pc", "http://ai-waker:8081/wake",
            cancelled=lambda: cancel_after is not None and clock.now >= cancel_after,
            progress=lambda p, s: None,
            up=lambda host: up_after is not None and clock.now >= up_after,
            send_wake=lambda url: wakes.append(clock.now),
            clock=clock, sleep=clock.sleep, **kw)
        return result, wakes, clock.now

    def test_already_awake_sends_no_wake(self):
        self.assertEqual(self.run_wait(up_after=0), (True, [], 0))

    def test_wakes_again_every_30_seconds_until_up(self):
        result, wakes, now = self.run_wait(up_after=75)
        self.assertTrue(result)
        self.assertEqual(wakes, [0, 30, 60])
        self.assertGreaterEqual(now, 75)

    def test_gives_up_after_five_minutes(self):
        result, wakes, now = self.run_wait()
        self.assertFalse(result)
        self.assertEqual(len(wakes), 10)
        self.assertGreaterEqual(now, 300)

    def test_cancel_stops_at_once(self):
        result, wakes, now = self.run_wait(cancel_after=10)
        self.assertFalse(result)
        self.assertLess(now, 15)

    def test_no_wake_url_still_waits(self):
        clock = Clock()
        sent = []
        ok = homelab_games.wait_until_up(
            "pc", "", cancelled=lambda: False, progress=lambda p, s: None,
            up=lambda h: clock.now >= 9, send_wake=sent.append,
            clock=clock, sleep=clock.sleep)
        self.assertTrue(ok)
        self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
