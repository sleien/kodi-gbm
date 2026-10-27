"""TV power over CEC, for callers that only have JSON-RPC (Home Assistant).

JSON-RPC cannot run Kodi builtins; it can run an add-on with arguments:
    Addons.ExecuteAddon {"addonid": "script.homelab.cec", "params": ["on"]}
"""
import sys

import xbmc

BUILTINS = {
    "on": "CECActivateSource",  # wakes the TV and switches it to Kodi
    "standby": "CECStandby",
    "toggle": "CECToggleState",
}

arg = sys.argv[1] if len(sys.argv) > 1 else ""
builtin = BUILTINS.get(arg)
if builtin:
    xbmc.executebuiltin(builtin)
else:
    xbmc.log("script.homelab.cec: expected on, standby or toggle, got %r" % arg,
             xbmc.LOGWARNING)
