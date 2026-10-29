"""Installs the add-ons in KODI_ADDONS through Kodi's own installer.

Kodi has no unattended install: the InstallAddon builtin asks "Do you want to
install …?" first. This answers that dialog with Yes, so dependencies are
resolved by Kodi exactly as for an install made by hand. Add-ons already
present are skipped, so it does nothing on every start after the first.

A skin, once installed, makes Kodi offer "Switch to it now?". That is
answered No: switching a running Kodi brings a "Keep this change?" dialog and
a race with the skin's own start-up scripts. Skins are chosen by KODI_SETTINGS
instead, which the entrypoint writes before Kodi starts; when something just
installed is named there, Kodi is restarted so it takes effect.

Kept free of Kodi imports so it can be tested with a fake `xbmc` module.
"""
YESNO_DIALOG = 10100  # WINDOW_DIALOG_YES_NO
YES_BUTTON = 11       # CGUIDialogYesNo's Yes button
NO_BUTTON = 10


def wanted(environ):
    return environ.get("KODI_ADDONS", "").split()


def missing(xbmc, addon_ids):
    return [a for a in addon_ids
            if not xbmc.getCondVisibility("System.HasAddon(%s)" % a)]


def decline_dialog(xbmc, monitor, seconds, poll=1):
    """Answer No to the first Yes/No dialog that opens within `seconds`."""
    waited = 0
    while waited < seconds:
        if xbmc.getCondVisibility("Window.IsActive(%d)" % YESNO_DIALOG):
            xbmc.executebuiltin("SendClick(%d,%d)" % (YESNO_DIALOG, NO_BUTTON))
            return
        if monitor.waitForAbort(poll):
            return
        waited += poll


def install(xbmc, monitor, addon_id, timeout=300, poll=1, skin_prompt=60):
    """Install one add-on; True once Kodi reports it installed."""
    xbmc.executebuiltin("InstallAddon(%s)" % addon_id)
    confirmed = False
    waited = 0
    while waited < timeout:
        if xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id):
            if addon_id.startswith("skin."):
                # "Switch to it now?" comes once its dependencies are in.
                decline_dialog(xbmc, monitor, skin_prompt, poll)
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


def needs_restart(installed, environ):
    """Installed add-ons that KODI_SETTINGS names, e.g. a skin to switch to."""
    named = set()
    for item in environ.get("KODI_SETTINGS", "").split():
        named.add(item.partition("=")[2])
    return [a for a in installed if a in named]
