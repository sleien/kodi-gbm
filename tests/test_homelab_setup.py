"""Tests for the add-on installer, against a fake Kodi.

    python3 -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "addons",
                                "service.homelab.setup", "resources", "lib"))

import homelab_setup  # noqa: E402


class FakeKodi:
    """Just enough of the xbmc module and Kodi's install dialog."""
    LOGINFO = 1
    LOGWARNING = 2

    def __init__(self, installed=(), installable=(), known_after_refresh=()):
        self.installed = set(installed)
        self.installable = set(installable)
        self.known_after_refresh = set(known_after_refresh)
        self.dialog_for = None
        self.builtins = []

    def getCondVisibility(self, cond):
        if cond.startswith("System.HasAddon("):
            return cond[len("System.HasAddon("):-1] in self.installed
        if cond == "Window.IsActive(10100)":
            return self.dialog_for is not None
        raise AssertionError("unexpected condition " + cond)

    def executebuiltin(self, builtin, wait=False):
        self.builtins.append(builtin)
        if builtin == "UpdateAddonRepos":
            self.installable |= self.known_after_refresh
        elif builtin.startswith("InstallAddon("):
            addon = builtin[len("InstallAddon("):-1]
            if addon in self.installable:
                self.dialog_for = addon
        elif builtin == "SendClick(10100,11)":
            assert self.dialog_for, "clicked Yes with no dialog open"
            self.installed.add(self.dialog_for)
            self.dialog_for = None

    def log(self, msg, level=0):
        pass


class FakeMonitor:
    def __init__(self, abort_after=None):
        self.waits = 0
        self.abort_after = abort_after

    def waitForAbort(self, seconds):
        self.waits += 1
        return self.abort_after is not None and self.waits >= self.abort_after


ENV = {"KODI_ADDONS": "plugin.video.youtube plugin.video.jellyfin"}


class InstallTests(unittest.TestCase):
    def test_installs_every_missing_addon_by_answering_yes(self):
        kodi = FakeKodi(installable={"plugin.video.youtube", "plugin.video.jellyfin"})
        self.assertEqual(homelab_setup.run(kodi, FakeMonitor(), ENV, settle=0), [])
        self.assertEqual(kodi.installed, {"plugin.video.youtube", "plugin.video.jellyfin"})
        self.assertEqual(kodi.builtins.count("SendClick(10100,11)"), 2)

    def test_installed_addons_are_left_alone(self):
        kodi = FakeKodi(installed={"plugin.video.youtube", "plugin.video.jellyfin"})
        self.assertEqual(homelab_setup.run(kodi, FakeMonitor(), ENV), [])
        self.assertEqual(kodi.builtins, [])

    def test_an_addon_found_only_after_a_repository_refresh_is_retried(self):
        kodi = FakeKodi(installable={"plugin.video.youtube"},
                        known_after_refresh={"plugin.video.jellyfin"})
        # The first refresh already knows youtube; jellyfin appears on the second.
        kodi.known_after_refresh = set()
        refreshes = []
        original = kodi.executebuiltin

        def executebuiltin(builtin, wait=False):
            if builtin == "UpdateAddonRepos":
                refreshes.append(1)
                if len(refreshes) == 2:
                    kodi.installable.add("plugin.video.jellyfin")
            original(builtin, wait)
        kodi.executebuiltin = executebuiltin

        failed = homelab_setup.run(kodi, FakeMonitor(), ENV, settle=0)
        self.assertEqual(failed, [])
        self.assertEqual(len(refreshes), 2)

    def test_reports_what_never_installs(self):
        kodi = FakeKodi(installable={"plugin.video.youtube"})
        failed = homelab_setup.run(kodi, FakeMonitor(), ENV, attempts=2, settle=0)
        self.assertEqual(failed, ["plugin.video.jellyfin"])

    def test_stops_when_kodi_quits(self):
        kodi = FakeKodi(installable={"plugin.video.youtube", "plugin.video.jellyfin"})
        failed = homelab_setup.run(kodi, FakeMonitor(abort_after=1), ENV)
        self.assertEqual(failed, ["plugin.video.youtube", "plugin.video.jellyfin"])
        self.assertNotIn("SendClick(10100,11)", kodi.builtins)

    def test_nothing_wanted_means_nothing_done(self):
        kodi = FakeKodi()
        self.assertEqual(homelab_setup.run(kodi, FakeMonitor(), {}), [])
        self.assertEqual(kodi.builtins, [])


if __name__ == "__main__":
    unittest.main()
