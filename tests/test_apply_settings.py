"""Tests for writing KODI_SETTINGS into guisettings.xml before Kodi starts."""
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import apply_settings  # noqa: E402

GUISETTINGS = """<settings version="2">
    <setting id="lookandfeel.skin" default="true">skin.estuary</setting>
    <setting id="services.webskin">webinterface.default</setting>
    <setting id="videoplayer.adjustrefreshrate">0</setting>
</settings>
"""


class ApplyTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(fd, "w") as f:
            f.write(GUISETTINGS)

    def tearDown(self):
        os.remove(self.path)

    def values(self):
        root = ET.parse(self.path).getroot()
        return {n.get("id"): (n.text, n.get("default")) for n in root.findall("setting")}

    def test_sets_changes_adds_and_leaves(self):
        env = {"KODI_SETTINGS": "lookandfeel.skin=skin.arctic.zephyr.mod "
                                "services.webskin=webinterface.tex "
                                "videoplayer.adjustrefreshrate=0 "
                                "audiooutput.audiodevice=ALSA:hdmi:CARD=Generic,DEV=1"}
        changed = apply_settings.apply(self.path, apply_settings.wanted(env))
        self.assertEqual(changed, ["lookandfeel.skin", "services.webskin",
                                   "audiooutput.audiodevice"])
        self.assertEqual(self.values(), {
            "lookandfeel.skin": ("skin.arctic.zephyr.mod", None),
            "services.webskin": ("webinterface.tex", None),
            "videoplayer.adjustrefreshrate": ("0", None),
            "audiooutput.audiodevice": ("ALSA:hdmi:CARD=Generic,DEV=1", None),
        })

    def test_a_default_marked_value_is_pinned(self):
        # The same text, but Kodi's "default" mark would let a future default win.
        env = {"KODI_SETTINGS": "lookandfeel.skin=skin.estuary"}
        self.assertEqual(apply_settings.apply(self.path, apply_settings.wanted(env)),
                         ["lookandfeel.skin"])
        self.assertEqual(self.values()["lookandfeel.skin"], ("skin.estuary", None))

    def test_nothing_to_do_leaves_the_file_alone(self):
        before = os.stat(self.path).st_mtime_ns
        env = {"KODI_SETTINGS": "videoplayer.adjustrefreshrate=0"}
        self.assertEqual(apply_settings.apply(self.path, apply_settings.wanted(env)), [])
        self.assertEqual(os.stat(self.path).st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
