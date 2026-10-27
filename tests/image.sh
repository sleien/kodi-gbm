#!/bin/sh
# Checks a built image: Kodi can run on GBM, the YouTube add-on's DASH input
# stream is present, and the entrypoint seeds exactly what it promises.
#
#   tests/image.sh <image>
set -eu

IMAGE=${1:?usage: tests/image.sh <image>}
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
ok() { printf 'ok: %s\n' "$*"; }
run() { docker run --rm --entrypoint /bin/sh "$IMAGE" -c "$1"; }

# Debian names it "Kodi from Debian Media Center 21.x".
run 'kodi --version' | grep -qE '^Kodi .*Media Center 21\.' \
  || fail "kodi --version does not report Kodi 21"
ok "Kodi 21"

# Debian builds one kodi.bin with every windowing system; --help lists them.
run 'kodi --help' | grep -A1 -- '--windowing' | grep -q 'gbm' \
  || fail "this Kodi has no GBM windowing"
ok "GBM windowing built"

run 'ls /usr/lib/x86_64-linux-gnu/kodi/addons/inputstream.adaptive/' \
  | grep -qx 'inputstream.adaptive.so' \
  || fail "inputstream.adaptive not installed"
ok "inputstream.adaptive"

for a in repository.jellyfin.kodi service.homelab.setup script.homelab.cec; do
  run "test -f /usr/share/kodi/addons/$a/addon.xml && grep -q '<addon optional=\"true\">$a</addon>' /usr/share/kodi/system/addon-manifest.xml" \
    || fail "$a is not built in and listed in the manifest"
done
ok "built-in add-ons enabled by the manifest"

# Single quotes on purpose: the expansion happens inside the container.
# shellcheck disable=SC2016
run 'test "$(id -u)" = 1000 && test "$HOME" = /home/kodi' \
  || fail "not running as uid 1000 with HOME=/home/kodi"
ok "uid 1000"

# Seeding, in a throwaway home, as the caller's uid: the stack runs the image
# as ${PUID}:${PGID}, and files written as another uid would be unreadable here.
as_me="$(id -u):$(id -g)"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
chmod 0777 "$tmp"
printf '<favourites/>\n' >"$tmp/favourites.xml"
chmod 0644 "$tmp/favourites.xml"

docker run --rm --user "$as_me" -e KODI_SEED_ONLY=1 -e 'KODI_WEB_PASSWORD=p&ss<w>rd' \
  -e YOUTUBE_API_KEY=AIzaTEST -e YOUTUBE_CLIENT_ID=123-abc.apps.googleusercontent.com \
  -e YOUTUBE_CLIENT_SECRET=GOCSPX-test \
  -v "$tmp:/home/kodi/.kodi" -v "$tmp/favourites.xml:/seed/favourites.xml:ro" \
  "$IMAGE" || fail "entrypoint failed to seed"

u=$tmp/userdata
grep -q '<setting id="services.webserverpassword">p&amp;ss&lt;w&gt;rd</setting>' "$u/guisettings.xml" \
  || fail "web server password not seeded, or not escaped"
grep -q '<setting id="audiooutput.truehdpassthrough">false</setting>' "$u/guisettings.xml" \
  || fail "TrueHD passthrough not off"
ok "guisettings.xml"

cmp -s "$tmp/favourites.xml" "$u/favourites.xml" || fail "favourites.xml not seeded"
ok "favourites.xml"

grep -q '"client_id": "123-abc"' "$u/addon_data/plugin.video.youtube/api_keys.json" \
  || fail "YouTube keys not seeded, or client ID suffix kept"
ok "api_keys.json"

# A second start changes nothing that Kodi now owns.
printf 'edited on the TV\n' >"$u/guisettings.xml"
docker run --rm --user "$as_me" -e KODI_SEED_ONLY=1 -e KODI_WEB_PASSWORD=other \
  -v "$tmp:/home/kodi/.kodi" "$IMAGE" || fail "second start failed"
[ "$(cat "$u/guisettings.xml")" = "edited on the TV" ] || fail "seed overwrote guisettings.xml"
ok "seeds never overwrite"

# The add-on's own empty store, written on its first run, still gets the keys.
rm "$u/addon_data/plugin.video.youtube/api_keys.json"
printf '{\n    "keys": {\n        "user": {\n            "api_key": "",\n            "client_id": "",\n            "client_secret": ""\n        },\n        "developer": {}\n    }\n}\n' \
  >"$u/addon_data/plugin.video.youtube/api_keys.json"
docker run --rm --user "$as_me" -e KODI_SEED_ONLY=1 -e KODI_WEB_PASSWORD=x \
  -e YOUTUBE_API_KEY=AIzaLATER -e YOUTUBE_CLIENT_ID=456-def -e YOUTUBE_CLIENT_SECRET=GOCSPX-later \
  -v "$tmp:/home/kodi/.kodi" "$IMAGE" || fail "third start failed"
grep -q '"api_key": "AIzaLATER"' "$u/addon_data/plugin.video.youtube/api_keys.json" \
  || fail "keys added later did not replace the add-on's empty store"
docker run --rm --user "$as_me" -e KODI_SEED_ONLY=1 -e KODI_WEB_PASSWORD=x \
  -e YOUTUBE_API_KEY=AIzaOTHER -e YOUTUBE_CLIENT_ID=789-ghi -e YOUTUBE_CLIENT_SECRET=GOCSPX-other \
  -v "$tmp:/home/kodi/.kodi" "$IMAGE" || fail "fourth start failed"
grep -q '"api_key": "AIzaLATER"' "$u/addon_data/plugin.video.youtube/api_keys.json" \
  || fail "a key already in the store was overwritten"
ok "YouTube keys arrive late, and are never overwritten"

# Kodi's Exit (code 0) keeps the container up; a crash exits with its code.
# A stub kodi on PATH stands in for the real one, which needs a display.
stub() {
  docker run --rm --user "$as_me" -e KODI_WEB_PASSWORD=x -v "$tmp:/home/kodi/.kodi" \
    --entrypoint /bin/sh "$IMAGE" -c "mkdir -p /tmp/bin && printf '#!/bin/sh\nexit $1\n' >/tmp/bin/kodi && chmod +x /tmp/bin/kodi && PATH=/tmp/bin:\$PATH timeout 5 /usr/local/bin/entrypoint.sh"
}
set +e
stub 3 >/dev/null 2>&1; crashed=$?
stub 0 >/dev/null 2>&1; exited=$?
set -e
[ "$crashed" = 3 ] || fail "a crash should exit with Kodi's code, got $crashed"
[ "$exited" = 124 ] || fail "Kodi's Exit should leave the container running, got $exited"
ok "Exit releases the display and stays up; a crash restarts"

# No password: the first start refuses rather than run an open web server.
tmp2=$(mktemp -d); chmod 0777 "$tmp2"
if docker run --rm --user "$as_me" -e KODI_SEED_ONLY=1 -v "$tmp2:/home/kodi/.kodi" "$IMAGE" 2>/dev/null; then
  rm -rf "$tmp2"; fail "first start without KODI_WEB_PASSWORD succeeded"
fi
rm -rf "$tmp2"
ok "first start requires a password"
