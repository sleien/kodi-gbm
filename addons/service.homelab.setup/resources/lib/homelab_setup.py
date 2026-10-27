"""Installs the add-ons named in KODI_ADDONS through Kodi's own installer.

Kodi has no unattended install: the InstallAddon builtin asks "Do you want to
install …?" first. This answers that dialog with Yes, so dependencies are
resolved by Kodi exactly as for an install made by hand. Add-ons already
present are skipped, so it does nothing on every start after the first.

Kept free of Kodi imports so it can be tested with a fake `xbmc` module.
"""

YESNO_DIALOG = 10100  # WINDOW_DIALOG_YES_NO
YES_BUTTON = 11       # CGUIDialogYesNo's Yes button


def wanted(environ):
    return environ.get("KODI_ADDONS", "").split()


def missing(xbmc, addon_ids):
    return [a for a in addon_ids
            if not xbmc.getCondVisibility("System.HasAddon(%s)" % a)]


def install(xbmc, monitor, addon_id, timeout=300, poll=1):
    """Install one add-on; True once Kodi reports it installed."""
    xbmc.executebuiltin("InstallAddon(%s)" % addon_id)
    confirmed = False
    waited = 0
    while waited < timeout:
        if xbmc.getCondVisibility("System.HasAddon(%s)" % addon_id):
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
