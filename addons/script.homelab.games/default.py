"""Hands the screen to Moonlight (kodi-gbm's entrypoint).

Kodi and Moonlight cannot both hold the display. This wakes the gaming PC
(MOONLIGHT_WAKE_URL) and waits, with a progress dialog, until Sunshine
answers; only then it leaves a note for the entrypoint and quits Kodi. The
entrypoint runs Moonlight, then starts Kodi again.

    RunScript(script.homelab.games)         stream MOONLIGHT_APP
    RunScript(script.homelab.games,pair)    pair with Sunshine; shows a PIN
"""
import os
import sys

import xbmc
import xbmcaddon
import xbmcgui

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib"))

import homelab_games  # noqa: E402

MODES = ("stream", "pair")
mode = sys.argv[1] if len(sys.argv) > 1 else "stream"
host = os.environ.get("MOONLIGHT_HOST", "")

if mode not in MODES:
    xbmc.log("script.homelab.games: expected stream or pair, got %r" % mode, xbmc.LOGWARNING)
elif not host:
    xbmc.executebuiltin("Notification(Games,MOONLIGHT_HOST is not set,8000)")
else:
    dialog = xbmcgui.DialogProgress()
    dialog.create("Games", "Waking the gaming PC…")
    monitor = xbmc.Monitor()

    def progress(percent, seconds):
        dialog.update(percent, "Waking the gaming PC… %d s" % seconds)

    up = homelab_games.wait_until_up(
        host, os.environ.get("MOONLIGHT_WAKE_URL", ""),
        cancelled=lambda: dialog.iscanceled() or monitor.abortRequested(),
        progress=progress, sleep=lambda s: monitor.waitForAbort(s))
    dialog.close()
    if not up:
        xbmc.executebuiltin("Notification(Games,The gaming PC did not answer,8000)")
    else:
        # special://temp; the entrypoint reads the same file.
        note = os.path.join(os.path.expanduser("~"), ".kodi", "temp", "kodi-gbm-launch")
        with open(note, "w") as f:
            f.write(mode)
        xbmc.executebuiltin("Notification(Games,%s,3000)"
                            % ("Pairing with the gaming PC" if mode == "pair" else "Starting the game stream"))
        xbmc.sleep(1500)
        xbmc.executebuiltin("Quit")
