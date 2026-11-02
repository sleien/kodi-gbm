"""Tests for upmixing music only."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addons",
                                "service.homelab.musicupmix", "resources", "lib"))

import musicupmix  # noqa: E402


class FakeKodi:
    def __init__(self, upmix):
        self.upmix = upmix
        self.sets = []

    def executeJSONRPC(self, request):
        req = json.loads(request)
        assert req["params"]["setting"] == "audiooutput.stereoupmix"
        if req["method"] == "Settings.GetSettingValue":
            return json.dumps({"id": 1, "result": {"value": self.upmix}})
        self.upmix = req["params"]["value"]
        self.sets.append(self.upmix)
        return json.dumps({"id": 1, "result": True})


class UpmixTests(unittest.TestCase):
    def test_music_only(self):
        self.assertTrue(musicupmix.wanted_for(True, False))
        self.assertFalse(musicupmix.wanted_for(False, True))
        self.assertFalse(musicupmix.wanted_for(True, True))   # a music video
        self.assertFalse(musicupmix.wanted_for(False, False))  # stopped

    def test_switches_only_when_it_differs(self):
        kodi = FakeKodi(False)
        self.assertTrue(musicupmix.set_upmix(kodi, True))
        self.assertFalse(musicupmix.set_upmix(kodi, True))
        self.assertTrue(musicupmix.set_upmix(kodi, False))
        self.assertEqual(kodi.sets, [True, False])


if __name__ == "__main__":
    unittest.main()
