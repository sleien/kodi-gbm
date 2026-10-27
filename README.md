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

## First start

`entrypoint.sh` seeds three files when they are absent, then starts Kodi.
After that, Kodi owns them, and changes made on the TV win.

| File | From | What |
|---|---|---|
| `userdata/guisettings.xml` | `KODI_WEB_USER` (default `kodi`), `KODI_WEB_PASSWORD` (required) | web server with a login; JSON-RPC from other machines; no Zeroconf, UPnP or AirPlay; no unknown add-on sources; passthrough of AC3, E-AC3 and DTS but not TrueHD or DTS-HD, which plain HDMI ARC cannot carry |
| `userdata/favourites.xml` | `/seed/favourites.xml`, if mounted | the home screen's favourites |
| `userdata/addon_data/plugin.video.youtube/api_keys.json` | `YOUTUBE_API_KEY`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, all three | personal API keys for the YouTube add-on, in its 7.x store format. Also written over the add-on's own empty store, so keys can arrive after the first start; a key already set is never replaced |

`KODI_SEED_ONLY=1` seeds and exits; the tests use it.

**CEC settings are not seeded.** Pulse-Eight's defaults switch the TV on and
to Kodi's input whenever Kodi starts, which means at every reboot. Set them in
Kodi, under Settings → System → Input → Peripherals → CEC Adapter, once the
adapter is plugged in.

**Exit is the way to the host's console.** Choosing Exit in Kodi's power
menu ends Kodi with code 0. The container then stays up without Kodi, the
display goes back to the kernel's text console, and a keyboard on the host
reaches its login prompt. `docker restart kodi`, or a reboot, starts Kodi
again.

**A crash exits the container** with Kodi's code. The restart policy brings it
back, and the crash shows in `docker ps` and in the logs. There is no restart
loop inside the container.

## Releasing

`tests/image.sh <image>` checks a build. CI runs it, then publishes `main`
and `sha-` tags on every push and semver tags on `v*.*.*`. The Kodi version is
whatever Debian trixie ships when the image is built; the image's semver is
this repository's own.
