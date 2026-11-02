"""Upmix for music only (resources/lib/musicupmix.py), when KODI_MUSIC_UPMIX=1."""
import os
import sys

import xbmc
import xbmcaddon

sys.path.insert(0, os.path.join(xbmcaddon.Addon().getAddonInfo("path"), "resources", "lib"))

import musicupmix  # noqa: E402


class UpmixPlayer(xbmc.Player):
    def apply(self):
        try:
            on = musicupmix.wanted_for(self.isPlayingAudio(), self.isPlayingVideo())
            if musicupmix.set_upmix(xbmc, on):
                xbmc.log("homelab musicupmix: upmix %s" % ("on" if on else "off"), xbmc.LOGINFO)
        except Exception as e:  # a failed switch must never stop playback
            xbmc.log("homelab musicupmix: %s" % e, xbmc.LOGWARNING)

    def onAVStarted(self):
        self.apply()

    def onPlayBackStopped(self):
        self.apply()

    def onPlayBackEnded(self):
        self.apply()


if os.environ.get("KODI_MUSIC_UPMIX") == "1":
    player = UpmixPlayer()
    monitor = xbmc.Monitor()
    player.apply()
    while not monitor.abortRequested():
        if monitor.waitForAbort(60):
            break
