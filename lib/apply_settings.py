"""Writes KODI_SETTINGS into guisettings.xml, before Kodi starts.

KODI_SETTINGS holds space-separated `setting.id=value` pairs, with the value
as guisettings.xml stores it (`true`, `0`, `skin.estuary`). Each is written
on every start, so the environment stays the one home for these settings: a
change made on the TV lasts until the next start. Kodi is not running, so it
applies them as it loads, without the dialogs a change at runtime would bring
(a new skin asks "Keep this change?").

    python3 -I apply_settings.py <guisettings.xml>
"""
import os
import sys
import xml.etree.ElementTree as ET


def wanted(environ):
    pairs = []
    for item in environ.get("KODI_SETTINGS", "").split():
        key, sep, value = item.partition("=")
        if sep and key:
            pairs.append((key, value))
    return pairs


def apply(path, pairs):
    """Returns the setting IDs whose stored value changed."""
    tree = ET.parse(path)
    root = tree.getroot()
    changed = []
    for key, value in pairs:
        node = root.find("setting[@id='%s']" % key)
        if node is None:
            node = ET.SubElement(root, "setting", {"id": key})
        if node.text == value and "default" not in node.attrib:
            continue
        node.text = value
        node.attrib.pop("default", None)
        changed.append(key)
    if changed:
        tmp = path + ".tmp"
        tree.write(tmp, encoding="utf-8", xml_declaration=False)
        os.replace(tmp, path)
    return changed


if __name__ == "__main__":
    for key in apply(sys.argv[1], wanted(os.environ)):
        print("entrypoint: set %s" % key, file=sys.stderr)
