# Kodi drawing straight to the display through DRM/KMS (--windowing=gbm): no X11,
# no Wayland, no display server anywhere. Built for sleien/homelab's `kodi`
# stack, which passes in /dev/dri, /dev/snd, /dev/input and a USB-CEC adapter.
#
# Kodi comes from Debian's own package, so it is the version Debian ships for
# trixie (21.2) with Debian's security fixes. The image is pinned by digest
# where it is used; Renovate proposes the base image's digest bumps here.
FROM debian:trixie-slim@sha256:62bd423aeee912639ca8ee681c2b762cb3e25137e0a92b20be455898a9f034ad

# kodi-inputstream-adaptive: DASH playback, which the YouTube add-on needs.
# kodi-repository-kodi: the official add-on repository, the only one enabled.
# mesa-va-drivers: VA-API decoding on AMD (radeonsi), the host this is for.
# vainfo, alsa-utils, cec-utils: for diagnosing the hardware from a shell in
# the container (`docker exec kodi vainfo`, `aplay -l`, `cec-client -l`).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      kodi \
      kodi-inputstream-adaptive \
      kodi-repository-kodi \
      mesa-va-drivers \
      vainfo \
      alsa-utils \
      cec-utils \
      ca-certificates \
      tini \
 && rm -rf /var/lib/apt/lists/*

# uid/gid 1000, matching PUID/PGID on the homelab host. The stack runs it as
# ${PUID}:${PGID} anyway; this gives that uid a home and a name. The home is
# traversable by any uid, so a host whose PUID is not 1000 still reaches the
# ~/.kodi it mounts there.
RUN groupadd --gid 1000 kodi \
 && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/kodi kodi \
 && chmod 0755 /home/kodi

COPY entrypoint.sh /usr/local/bin/entrypoint.sh

ENV HOME=/home/kodi
USER 1000:1000
WORKDIR /home/kodi

# 8080: web server and JSON-RPC over HTTP. 9090: JSON-RPC over TCP/WebSocket.
EXPOSE 8080 9090

# -g: signals go to the whole process group, so `docker stop` reaches Kodi,
# which the entrypoint runs as a child rather than exec'ing.
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/entrypoint.sh"]
