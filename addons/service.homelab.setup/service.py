"""Installs the TV box's add-ons on Kodi's start (resources/lib/homelab_setup.py)."""
import os
import sys

import xbmc
import xbmcaddon

sys.path.insert(0, os.path.join(
    xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib"))

import homelab_setup  # noqa: E402

monitor = xbmc.Monitor()
# Let the home screen and the repository check that Kodi runs at start settle.
if not monitor.waitForAbort(10):
    failed = homelab_setup.run(xbmc, monitor, os.environ)
    if failed:
        xbmc.log("homelab setup: not installed: %s" % " ".join(failed),
                 xbmc.LOGWARNING)
        xbmc.executebuiltin("Notification(TV setup,Not installed: %s,15000)"
                            % ", ".join(failed))
    if not monitor.abortRequested():
        changed, unset = homelab_setup.apply_settings(xbmc, monitor, os.environ)
        if changed:
            xbmc.log("homelab setup: set %s" % " ".join(changed), xbmc.LOGINFO)
        if unset:
            xbmc.executebuiltin("Notification(TV setup,Settings not applied: %s,15000)"
                                % ", ".join(unset))
