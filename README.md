# kodi-gbm

Kodi in a container, drawing straight to a display through DRM/KMS
(`--windowing=gbm`). No X11, no Wayland, no display server on the host or in
the container. Built for the `kodi` stack in
[sleien/homelab](https://github.com/sleien/homelab), where a headless Docker
host drives the living-room TV over HDMI.

- **Kodi 21** from Debian trixie's package, with `inputstream.adaptive` (DASH,
  which the YouTube add-on needs) and the official add-on repository.
- **VA-API** through Mesa (`radeonsi`), for the AMD iGPU this is built for.
  Intel would need `intel-media-va-driver` added.
- **CEC** through libcec, for a Pulse-Eight USB-CEC adapter.
- **Runs as uid 1000.** Kodi's home is `/home/kodi/.kodi`.

## Running it

The container needs the display, sound and input devices, and nothing that
would let it take over the host:

```yaml
services:
  kodi:
    image: ghcr.io/sleien/kodi-gbm:<version>@sha256:<digest>
    user: "1000:1000"
    devices:
      - /dev/dri/card1        # the card with the HDMI connector
      - /dev/dri/renderD128
      - /dev/snd
      - /dev/input
      - /dev/serial/by-id/usb-Pulse-Eight_CEC_Adapter-if00:/dev/ttyACM0
    group_add: ["44", "29", "20"]   # the host's video, audio, dialout gids, plus render and input
    volumes:
      - ./data:/home/kodi/.kodi
      - /run/udev:/run/udev:ro
    environment:
      KODI_WEB_PASSWORD: change-me
    ports:
      - 192.168.1.220:8089:8080
      - 192.168.1.220:9090:9090
```

Nothing else may hold the display: no desktop session, no other DRM client.
The kernel's text console is fine; Kodi takes the display over from it.

## Built-in add-ons

Four add-ons are built into Kodi's system directory and listed in its
manifest. That is what makes Kodi enable them on a fresh profile; add-ons
that appear any other way start disabled.

| Add-on | What it does |
|---|---|
| `repository.jellyfin.kodi` | Jellyfin's own repository, where Jellyfin for Kodi and JellyCon live. Neither is in a Kodi repository. The zip is pinned by checksum. |
| `repository.siku2` | SponsorBlock's author's repository: SponsorBlock (`script.service.sponsorblock`), which skips sponsor segments in YouTube videos, is in no Kodi repository either. The zip is pinned by checksum. |
| `service.homelab.setup` | On every start, installs each add-on named in `KODI_ADDONS` (space-separated IDs) that is missing. It goes through Kodi's own installer, which resolves dependencies, by answering the "Install?" dialog with Yes. It retries after a repository refresh, and shows a notification for what it could not install. |
| `script.homelab.cec` | TV power over CEC for callers that only have JSON-RPC: `Addons.ExecuteAddon` with `addonid` `script.homelab.cec` and `params` `["on"]`, `["standby"]` or `["toggle"]`. |

For example, `KODI_ADDONS="plugin.video.youtube plugin.video.jellyfin"`.

A skin offers "Switch to it now?" once installed; the service answers No.
Switching a running Kodi brings a "Keep this change?" dialog and races the
skin's own start-up scripts. One skin's menu builder once wrote into the
previous skin's read-only folder that way. Skins and other settings come from
`KODI_SETTINGS` instead (next section). When something just installed is
named there, the service restarts Kodi so it takes effect.

## First start

`entrypoint.sh` seeds three files when they are absent, then starts Kodi.
After that, Kodi owns them, and changes made on the TV win.

| File | From | What |
|---|---|---|
| `userdata/guisettings.xml` | `KODI_WEB_USER` (default `kodi`), `KODI_WEB_PASSWORD` (required) | web server with a login; JSON-RPC from other machines; no Zeroconf, UPnP or AirPlay; no unknown add-on sources; passthrough of AC3, E-AC3 and DTS but not TrueHD or DTS-HD, which plain HDMI ARC cannot carry |
| `userdata/favourites.xml` | `/seed/favourites.xml`, if mounted | the home screen's favourites |
| `userdata/addon_data/plugin.video.youtube/api_keys.json` | `YOUTUBE_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, all three | personal API keys for the YouTube add-on, in its 7.x store format. Also written over the add-on's own empty store, so keys can arrive after the first start; a key already set is never replaced |

**`KODI_SETTINGS`**, space-separated `setting.id=value` pairs as
`guisettings.xml` stores them, is written into `guisettings.xml` before every
start of Kodi, for example
`KODI_SETTINGS="lookandfeel.skin=skin.arctic.zephyr.mod services.webskin=webinterface.tex"`.
Kodi is not running at that moment, so it loads them directly: a new skin
starts without any dialog. These settings belong to whoever sets the
environment: a change made on the TV lasts until the next start.

**`KODI_SOURCES`**, space-separated `type:name:path` entries such as
`music:Music:/music/`, is merged into `sources.xml` before every start. A
source whose path is missing from its section is added; nothing is removed,
and what Kodi or its add-ons wrote there stays. Jellyfin for Kodi keeps its
own entries in the same file.

`KODI_SEED_ONLY=1` seeds, applies `KODI_SOURCES` and `KODI_SETTINGS`, and
exits; the tests use it.

**CEC settings are not seeded.** Pulse-Eight's defaults switch the TV on and
to Kodi's input whenever Kodi starts, which means at every reboot. Set them in
Kodi, under Settings → System → Input → Peripherals → CEC Adapter, once the
adapter is plugged in.

**Exit is the way to the host's console.** Choosing Exit in Kodi's power
menu ends Kodi with code 0. The container then stays up without Kodi, the
display goes back to the kernel's text console, and a keyboard on the host
reaches its login prompt. `docker restart kodi`, or a reboot, starts Kodi
again.

**RestartApp** (exit code 65) starts Kodi again inside the container, with
`KODI_SETTINGS` written first. Kodi's binary is run directly rather than
Debian's `/usr/bin/kodi` wrapper, which would restart it on 65 without the
entrypoint seeing it.

**A crash exits the container** with Kodi's code. The restart policy brings it
back, and the crash shows in `docker ps` and in the logs. There is no restart
loop inside the container.

## Releasing

`tests/image.sh <image>` checks a build. CI runs it, then publishes `main`
and `sha-` tags on every push and semver tags on `v*.*.*`. The Kodi version is
whatever Debian trixie ships when the image is built; the image's semver is
this repository's own.
