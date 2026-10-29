"""Installs the add-ons in KODI_ADDONS and applies the settings in KODI_SETTINGS.

Kodi has no unattended install: the InstallAddon builtin asks "Do you want to
install …?" first. This answers that dialog with Yes, so dependencies are
resolved by Kodi exactly as for an install made by hand. Add-ons already
present are skipped, so it does nothing on every start after the first.

KODI_SETTINGS holds space-separated `setting.id=value` pairs. Each is set
through JSON-RPC whenever Kodi's value differs, so the stack's compose file
stays the one home for them: a change made on the TV to one of these settings
lasts until the next start. A skin, installed or switched to, makes Kodi ask
"Switch to this skin?" and "Keep this change?"; both are answered Yes.

Kept free of Kodi imports so it can be tested with a fake `xbmc` module.
"""
import json

YESNO_DIALOG = 10100  # WINDOW_DIALOG_YES_NO
YES_BUTTON = 11       # CGUIDialogYesNo's Yes button


def wanted(environ):
    return environ.get("KODI_ADDONS", "").split()


def missing(xbmc, addon_ids):
    return [a for a in addon_ids
            if not xbmc.getCondVisibility("System.HasAddon(%s)" % a)]


def confirm_dialogs(xbmc, monitor, seconds, poll=1):
    """Answer Yes to every Yes/No dialog that opens within `seconds`."""
    waited = 0
    while waited < seconds:
        if xbmc.getCondVisibility("Window.IsActive(%d)" % YESNO_DIALOG):
            xbmc.executebuiltin("SendClick(%d,%d)" % (YESNO_DIALOG, YES_BUTTON))
        if monitor.waitForAbort(poll):
            return
        waited += poll


def install(xbmc, monitor, addon_id, timeout=300, poll=1, skin_confirm=20):
    """Install one add-on; True once Kodi reports it installed."""
    xbmc.executebuiltin("InstallAddon(%s)" % addon_id)
    confirmed = False
    waited = 0
    while waited < timeout:
        if xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id):
            if addon_id.startswith("skin."):
                confirm_dialogs(xbmc, monitor, skin_confirm, poll)
            return True
        if not confirmed and xbmc.getCondVisibility(
                "Window.IsActive(%d)" % YESNO_DIALOG):
            xbmc.executebuiltin("SendClick(%d,%d)" % (YESNO_DIALOG, YES_BUTTON))
            confirmed = True
        if monitor.waitForAbort(poll):
            return False
        waited += poll
    return False


def run(xbmc, monitor, environ, attempts=3, settle=20):
    """Install what is missing; returns the add-on IDs that failed.

    A fresh profile has not fetched its repositories yet, so an add-on Kodi
    cannot find yet is retried after asking for a repository refresh.
    """
    todo = missing(xbmc, wanted(environ))
    for attempt in range(attempts):
        if not todo:
            return []
        xbmc.log("homelab setup: installing %s (attempt %d)"
                 % (" ".join(todo), attempt + 1), xbmc.LOGINFO)
        xbmc.executebuiltin("UpdateAddonRepos", True)
        if monitor.waitForAbort(settle):
            return todo
        todo = [a for a in todo if not install(xbmc, monitor, a)]
    return todo


def wanted_settings(environ):
    pairs = []
    for item in environ.get("KODI_SETTINGS", "").split():
        key, sep, value = item.partition("=")
        if sep and key:
            pairs.append((key, value))
    return pairs


def rpc(xbmc, method, params):
    request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    if "error" in response:
        raise RuntimeError("%s: %s" % (method, response["error"]))
    return response["result"]


def coerce(current, value):
    """The text from KODI_SETTINGS, as the type Kodi holds the setting in."""
    if isinstance(current, bool):
        return value.lower() in ("true", "1", "yes", "on")
    if isinstance(current, int):
        return int(value)
    if isinstance(current, float):
        return float(value)
    return value


def apply_settings(xbmc, monitor, environ, skin_confirm=20):
    """Set what differs; returns (changed, failed) setting IDs."""
    changed, failed = [], []
    for key, text in wanted_settings(environ):
        try:
            current = rpc(xbmc, "Settings.GetSettingValue", {"setting": key})["value"]
            value = coerce(current, text)
            if current == value:
                continue
            rpc(xbmc, "Settings.SetSettingValue", {"setting": key, "value": value})
            changed.append(key)
            if key == "lookandfeel.skin":
                confirm_dialogs(xbmc, monitor, skin_confirm)
        except (RuntimeError, ValueError, KeyError) as e:
            xbmc.log("homelab setup: setting %s: %s" % (key, e), xbmc.LOGWARNING)
            failed.append(key)
    return changed, failed
