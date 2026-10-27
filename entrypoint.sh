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
YT_DIR=$USERDATA/addon_data/plugin.video.youtube
if [ ! -f "$YT_DIR/api_keys.json" ] \
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

if [ "${KODI_SEED_ONLY:-0}" = 1 ]; then
  exit 0
fi

# No kodi-standalone loop: when Kodi exits, the container exits and Docker's
# restart policy brings it back, so a crash shows in `docker ps` and the logs.
exec kodi --standalone --windowing=gbm --audio-backend=alsa
