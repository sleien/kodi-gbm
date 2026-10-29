"""Adds the sources in KODI_SOURCES to sources.xml, before Kodi starts.

KODI_SOURCES holds space-separated `type:name:path` entries, for example
`music:Music:/music/`. `type` is one of Kodi's source sections: video, music,
pictures, files, programs, games.

A source with that path is added to its section if no source there has it
yet. Nothing is removed and nothing else is touched: Kodi and its add-ons
(Jellyfin for Kodi among them) keep their own entries in the same file.

    python3 -I add_sources.py <sources.xml>
"""
import os
import sys
import xml.etree.ElementTree as ET

SECTIONS = ("programs", "video", "music", "pictures", "files", "games")


def wanted(environ):
    entries = []
    for item in environ.get("KODI_SOURCES", "").split():
        parts = item.split(":", 2)
        if len(parts) == 3 and parts[0] in SECTIONS and parts[1] and parts[2]:
            entries.append(tuple(parts))
    return entries


def add(path, entries):
    """Returns the paths added."""
    if os.path.exists(path):
        tree = ET.parse(path)
        root = tree.getroot()
    else:
        root = ET.Element("sources")
        tree = ET.ElementTree(root)
    added = []
    for section, name, source_path in entries:
        node = root.find(section)
        if node is None:
            node = ET.SubElement(root, section)
            ET.SubElement(node, "default", {"pathversion": "1"})
        if any(p.text == source_path for p in node.iter("path")):
            continue
        source = ET.SubElement(node, "source")
        ET.SubElement(source, "name").text = name
        ET.SubElement(source, "path", {"pathversion": "1"}).text = source_path
        ET.SubElement(source, "allowsharing").text = "true"
        added.append(source_path)
    if added:
        tmp = path + ".tmp"
        tree.write(tmp, encoding="utf-8", xml_declaration=False)
        os.replace(tmp, path)
    return added


if __name__ == "__main__":
    for p in add(sys.argv[1], wanted(os.environ)):
        print("entrypoint: added source %s" % p, file=sys.stderr)
