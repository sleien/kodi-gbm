"""Hands the screen to Moonlight (kodi-gbm's entrypoint).

Kodi and Moonlight cannot both hold the display, so this wakes the gaming PC
(MOONLIGHT_WAKE_URL), leaves a note for the entrypoint saying what to run,
and quits Kodi. The entrypoint runs Moonlight, then starts Kodi again.

    RunScript(script.homelab.games)         stream MOONLIGHT_APP
    RunScript(script.homelab.games,pair)    pair with Sunshine; shows a PIN
"""
import os
import sys
import urllib.request

import xbmc

MODES = ("stream", "pair")
mode = sys.argv[1] if len(sys.argv) > 1 else "stream"

if mode not in MODES:
    xbmc.log("script.homelab.games: expected stream or pair, got %r" % mode, xbmc.LOGWARNING)
elif not os.environ.get("MOONLIGHT_HOST"):
    xbmc.executebuiltin("Notification(Games,MOONLIGHT_HOST is not set,8000)")
else:
    wake = os.environ.get("MOONLIGHT_WAKE_URL")
    if wake:
        try:
            urllib.request.urlopen(urllib.request.Request(wake, data=b"", method="POST"), timeout=5)
        except Exception as e:  # Moonlight still tries; the PC may be awake
            xbmc.log("script.homelab.games: wake failed: %s" % e, xbmc.LOGWARNING)
    # special://temp; the entrypoint reads the same file.
    note = os.path.join(os.path.expanduser("~"), ".kodi", "temp", "kodi-gbm-launch")
    with open(note, "w") as f:
        f.write(mode)
    xbmc.executebuiltin("Notification(Games,%s,3000)"
                        % ("Pairing with the gaming PC" if mode == "pair" else "Starting the game stream"))
    xbmc.sleep(1500)
    xbmc.executebuiltin("Quit")
