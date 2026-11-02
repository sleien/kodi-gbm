"""Waking the gaming PC until Sunshine answers. Free of Kodi imports, so it
can be tested without Kodi."""
import time
import urllib.request


def sunshine_up(host, timeout=2, urlopen=urllib.request.urlopen):
    """True when Sunshine's serverinfo answers on the host."""
    try:
        with urlopen("http://%s:47989/serverinfo" % host, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wake(url, urlopen=urllib.request.urlopen):
    try:
        urlopen(urllib.request.Request(url, data=b"", method="POST"), timeout=5).close()
        return True
    except Exception:
        return False


def wait_until_up(host, wake_url, cancelled, progress, rewake_every=30,
                  give_up_after=300, poll=3, up=sunshine_up, send_wake=wake,
                  clock=time.monotonic, sleep=time.sleep):
    """Wake the PC and wait for Sunshine; True when it answers.

    A wake goes out at once and again every `rewake_every` seconds: one
    magic packet can get lost, or the PC can fall asleep again on the way.
    `progress(percent, seconds)` reports; `cancelled()` stops early.
    """
    start = clock()
    last_wake = None
    while True:
        elapsed = clock() - start
        if up(host):
            return True
        if elapsed >= give_up_after or cancelled():
            return False
        if wake_url and (last_wake is None or clock() - last_wake >= rewake_every):
            send_wake(wake_url)
            last_wake = clock()
        progress(min(99, int(100 * elapsed / give_up_after)), int(elapsed))
        sleep(poll)
