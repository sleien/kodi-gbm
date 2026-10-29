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
    before = homelab_setup.missing(xbmc, homelab_setup.wanted(os.environ))
    failed = homelab_setup.run(xbmc, monitor, os.environ)
    if failed:
        xbmc.log("homelab setup: not installed: %s" % " ".join(failed),
                 xbmc.LOGWARNING)
        xbmc.executebuiltin("Notification(TV setup,Not installed: %s,15000)"
                            % ", ".join(failed))
    installed = [a for a in before if a not in failed]
    restart_for = homelab_setup.needs_restart(installed, os.environ)
    if restart_for and not monitor.abortRequested():
        # The entrypoint applies KODI_SETTINGS before Kodi starts; a restart
        # is what puts a just-installed skin or web interface in use.
        xbmc.log("homelab setup: restarting Kodi for %s" % " ".join(restart_for),
                 xbmc.LOGINFO)
        xbmc.executebuiltin("Notification(TV setup,Restarting to apply %s,5000)"
                            % ", ".join(restart_for))
        if not monitor.waitForAbort(5):
            xbmc.executebuiltin("RestartApp")
