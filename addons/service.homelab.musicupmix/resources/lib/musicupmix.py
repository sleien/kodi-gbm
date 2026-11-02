"""Upmix stereo to the configured speaker layout for music only.

Kodi has one global "upmix" setting. Over HDMI ARC, multichannel sound only
reaches a soundbar as Dolby Digital, so with 5.1 channels and AC3 transcoding
set, upmixed music arrives as Dolby Digital 5.1 and plays on every channel.
Films keep their own mix: upmix is switched on when audio-only playback
starts and off for anything else. Free of Kodi imports, for testing.
"""
import json

SETTING = "audiooutput.stereoupmix"


def rpc(xbmc, method, params):
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if "error" in response:
        raise RuntimeError("%s: %s" % (method, response["error"]))
    return response["result"]


def set_upmix(xbmc, on):
    """Set upmix if it differs; True when it was changed."""
    if rpc(xbmc, "Settings.GetSettingValue", {"setting": SETTING})["value"] == on:
        return False
    rpc(xbmc, "Settings.SetSettingValue", {"setting": SETTING, "value": on})
    return True


def wanted_for(playing_audio, playing_video):
    """Upmix while music plays; never while video plays."""
    return bool(playing_audio and not playing_video)
