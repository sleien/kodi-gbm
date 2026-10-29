#!/bin/sh
# Seeds Kodi's configuration on first start, then runs Kodi on GBM.
#
# Every seed is written only if its file is absent: after the first start Kodi
# owns its configuration, and changes made on the TV win over the environment.
#
# Environment:
#   KODI_WEB_USER, KODI_WEB_PASSWORD    web server login (password required)
#   YOUTUBE_API_KEY, YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET
#                                       personal API keys; seeded only if all
#                                       three are set
#   KODI_SETTINGS                       setting.id=value pairs written into
#                                       guisettings.xml on every start
#   KODI_SOURCES                        type:name:path entries added to
#                                       sources.xml if their path is missing
#   KODI_SEED_ONLY=1                    seed, then exit instead of starting Kodi
set -eu

KODI_HOME=${HOME:-/home/kodi}/.kodi
USERDATA=$KODI_HOME/userdata

log() { printf 'entrypoint: %s\n' "$*" >&2; }

# XML text content: escape the five characters XML reserves.
xml_escape() {
  printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' \
                         -e 's/"/\&quot;/g' -e "s/'/\&apos;/g"
}

mkdir -p "$USERDATA"

# --- guisettings.xml --------------------------------------------------------
# Web server on with a login, JSON-RPC reachable from other machines, nothing
# announced on the network, and passthrough limited to what HDMI ARC carries:
# AC3, E-AC3 and DTS pass through; TrueHD and DTS-HD (eARC only) are decoded.
if [ ! -f "$USERDATA/guisettings.xml" ]; then
  : "${KODI_WEB_PASSWORD:?KODI_WEB_PASSWORD must be set for the first start}"
  _user=$(xml_escape "${KODI_WEB_USER:-kodi}")
  _pass=$(xml_escape "$KODI_WEB_PASSWORD")
  cat >"$USERDATA/guisettings.xml" <<EOF
<settings version="2">
    <setting id="services.webserver">true</setting>
    <setting id="services.webserverport">8080</setting>
    <setting id="services.webserverauthentication">true</setting>
    <setting id="services.webserverusername">$_user</setting>
    <setting id="services.webserverpassword">$_pass</setting>
    <setting id="services.esenabled">true</setting>
    <setting id="services.esallinterfaces">true</setting>
    <setting id="services.zeroconf">false</setting>
    <setting id="services.upnp">false</setting>
    <setting id="services.airplay">false</setting>
    <setting id="addons.unknownsources">false</setting>
    <setting id="audiooutput.volumesteps">90</setting>
    <setting id="audiooutput.passthrough">true</setting>
    <setting id="audiooutput.ac3passthrough">true</setting>
    <setting id="audiooutput.eac3passthrough">true</setting>
    <setting id="audiooutput.dtspassthrough">true</setting>
    <setting id="audiooutput.truehdpassthrough">false</setting>
    <setting id="audiooutput.dtshdpassthrough">false</setting>
</settings>
EOF
  log "seeded guisettings.xml"
fi

# --- favourites.xml ---------------------------------------------------------
if [ ! -f "$USERDATA/favourites.xml" ] && [ -f /seed/favourites.xml ]; then
  cp /seed/favourites.xml "$USERDATA/favourites.xml"
  log "seeded favourites.xml"
fi

# --- YouTube add-on API keys -------------------------------------------------
# The add-on's own store, format as of plugin.video.youtube 7.4.4
# (kodion/json_store/api_keys.py). The add-on copies these into its settings on
# its next run. Values are restricted to the characters Google's keys and IDs
# use, so they need no JSON escaping.
#
# Seeded when the store is absent, and also when it holds no personal key: the
# add-on writes an empty store on its own first run, so keys added to the
# environment after that would otherwise never arrive. A key set in the add-on
# is never overwritten.
YT_DIR=$USERDATA/addon_data/plugin.video.youtube
yt_keys_missing() {
  [ ! -f "$YT_DIR/api_keys.json" ] \
    || grep -Eq '"api_key"[[:space:]]*:[[:space:]]*""' "$YT_DIR/api_keys.json"
}
if yt_keys_missing \
   && [ -n "${YOUTUBE_API_KEY:-}" ] \
   && [ -n "${YOUTUBE_CLIENT_ID:-}" ] \
   && [ -n "${YOUTUBE_CLIENT_SECRET:-}" ]; then
  case "$YOUTUBE_API_KEY$YOUTUBE_CLIENT_ID$YOUTUBE_CLIENT_SECRET" in
    *[!A-Za-z0-9._-]*)
      log "YouTube keys contain unexpected characters; not seeded"
      ;;
    *)
      mkdir -p "$YT_DIR"
      _id=${YOUTUBE_CLIENT_ID%.apps.googleusercontent.com}
      cat >"$YT_DIR/api_keys.json" <<EOF
{"keys": {"user": {"api_key": "$YOUTUBE_API_KEY", "client_id": "$_id", "client_secret": "$YOUTUBE_CLIENT_SECRET"}, "developer": {}}}
EOF
      chmod 0600 "$YT_DIR/api_keys.json"
      log "seeded YouTube API keys"
      ;;
  esac
fi

# --- KODI_SETTINGS ----------------------------------------------------------
# Written into guisettings.xml before every start of Kodi, while it is not
# running (lib/apply_settings.py).
apply_settings() {
  if [ -n "${KODI_SOURCES:-}" ]; then
    python3 -I /usr/local/lib/kodi-gbm/add_sources.py "$USERDATA/sources.xml" \
      || log "KODI_SOURCES not applied: sources.xml unreadable"
  fi
  [ -n "${KODI_SETTINGS:-}" ] || return 0
  # A guisettings.xml it cannot parse must not keep Kodi from starting.
  python3 -I /usr/local/lib/kodi-gbm/apply_settings.py "$USERDATA/guisettings.xml" \
    || log "KODI_SETTINGS not applied: guisettings.xml unreadable"
}

if [ "${KODI_SEED_ONLY:-0}" = 1 ]; then
  apply_settings
  exit 0
fi

# Kodi's binary, not Debian's /usr/bin/kodi wrapper: the wrapper restarts
# Kodi itself on exit code 65 (RestartApp), and KODI_SETTINGS has to be
# written before each start. The wrapper's one relevant setting is the malloc
# threshold below.
KODI_BIN=${KODI_BIN:-/usr/lib/x86_64-linux-gnu/kodi/kodi.bin}
export MALLOC_MMAP_THRESHOLD_=131072

# Exit codes:
#  65 (RestartApp, used by the setup service after installing a skin):
#     start again here, with KODI_SETTINGS written first.
#  0  (Kodi's own Exit) is the way to the host's console: the container stays
#     up without Kodi, so the restart policy does not put Kodi back over
#     whoever just went there, and the kernel's console takes the display
#     again. `docker restart kodi`, or a reboot, starts Kodi again.
#  anything else is a crash: the container exits, Docker's restart policy
#     brings it back, and the crash shows in `docker ps` and the logs.
while :; do
  apply_settings
  set +e
  "$KODI_BIN" --standalone --windowing=gbm --audio-backend=alsa
  code=$?
  set -e
  [ "$code" -eq 65 ] || break
  log "Kodi asked to restart; starting it again"
done
if [ "$code" -ne 0 ]; then
  exit "$code"
fi
log "Kodi exited; the display is back on the host console." \
    "'docker restart kodi' starts Kodi again."
exec sleep infinity
