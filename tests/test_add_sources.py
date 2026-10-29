"""Tests for merging KODI_SOURCES into sources.xml."""
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import add_sources  # noqa: E402

# What Jellyfin for Kodi leaves in sources.xml, more or less.
EXISTING = """<sources>
    <programs><default pathversion="1"></default></programs>
    <video>
        <default pathversion="1"></default>
        <source><name>Jellyfin</name><path pathversion="1">http://127.0.0.1:57578/</path><allowsharing>true</allowsharing></source>
    </video>
</sources>
"""


class AddTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "sources.xml")

    def tearDown(self):
        for f in os.listdir(self.dir):
            os.remove(os.path.join(self.dir, f))
        os.rmdir(self.dir)

    def sources(self, section):
        root = ET.parse(self.path).getroot()
        return [(s.findtext("name"), s.findtext("path"))
                for s in root.find(section).findall("source")]

    def test_parses_entries_and_ignores_bad_ones(self):
        env = {"KODI_SOURCES": "music:Music:/music/ nonsense video:: badtype:X:/x/"}
        self.assertEqual(add_sources.wanted(env), [("music", "Music", "/music/")])

    def test_creates_the_file_when_absent(self):
        added = add_sources.add(self.path, [("music", "Music", "/music/")])
        self.assertEqual(added, ["/music/"])
        self.assertEqual(self.sources("music"), [("Music", "/music/")])

    def test_merges_and_keeps_what_others_wrote(self):
        with open(self.path, "w") as f:
            f.write(EXISTING)
        add_sources.add(self.path, [("music", "Music", "/music/")])
        self.assertEqual(self.sources("video"), [("Jellyfin", "http://127.0.0.1:57578/")])
        self.assertEqual(self.sources("music"), [("Music", "/music/")])

    def test_a_path_already_there_is_not_added_twice(self):
        add_sources.add(self.path, [("music", "Music", "/music/")])
        before = os.stat(self.path).st_mtime_ns
        self.assertEqual(add_sources.add(self.path, [("music", "Renamed", "/music/")]), [])
        self.assertEqual(os.stat(self.path).st_mtime_ns, before)
        self.assertEqual(self.sources("music"), [("Music", "/music/")])


if __name__ == "__main__":
    unittest.main()
