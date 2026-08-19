#!/usr/bin/env python3
"""Poll sorel.com for Kinetic Aura Slingback (style 2151361), color Black/Sea Salt (010),
size 9, and push a notification to ntfy.sh/mayada-shoes every time it's in stock.

Runs as a long loop (one check every CHECK_INTERVAL seconds) until RUN_SECONDS elapses;
GitHub Actions restarts it on a 6-hour schedule.
"""

import json
import ssl
import sys
import time
import urllib.request
import urllib.error
import http.cookiejar
from datetime import datetime, timezone

PID = "2151361"
COLOR = "010"          # "Black, Sea Salt"
SIZE = "9"
PRODUCT_URL = f"https://www.sorel.com/p/kinetic-aura-slingback-womens-sandal-{PID}.html"
BUY_URL = f"{PRODUCT_URL}?dwvar_{PID}_color={COLOR}&dwvar_{PID}_size={SIZE}"
VARIATION_URL = (
    "https://www.sorel.com/on/demandware.store/Sites-Sorel_US-Site/en_US/"
    f"Product-Variation?dwvar_{PID}_color={COLOR}&dwvar_{PID}_size={SIZE}&pid={PID}"
)
NTFY_URL = "https://ntfy.sh/mayada-shoes"

CHECK_INTERVAL = 120           # seconds between checks
RUN_SECONDS = 5 * 3600 + 45 * 60  # 5h45m, safely under the 6h GitHub job limit
BLOCKED_ALERT_THRESHOLD = 30   # consecutive failed checks before warning once per run

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

ssl_context = ssl.create_default_context()
try:
    import certifi
    ssl_context.load_verify_locations(certifi.where())
except ImportError:
    pass

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ssl_context),
    urllib.request.HTTPCookieProcessor(cookie_jar),
)


def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}", flush=True)


def fetch(url, accept="application/json", timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest" if accept == "application/json" else "",
    })
    with opener.open(req, timeout=timeout) as resp:
        return resp.read()


def warm_up():
    """Hit the product page so PerimeterX sets its cookies in our jar."""
    try:
        fetch(PRODUCT_URL, accept="text/html,application/xhtml+xml")
    except Exception as e:
        log(f"warm-up fetch failed: {e}")


def check_stock():
    """Return (available: bool, stocklevel: int). Raises on block/parse failure."""
    body = fetch(VARIATION_URL)
    data = json.loads(body)
    product = data.get("product", data)
    availability = product.get("availability", {})
    stocklevel = availability.get("stocklevel", 0) or 0
    instock = availability.get("instock", 0) or 0
    available = bool(product.get("available")) or instock > 0 or stocklevel > 0
    return available, stocklevel


def notify(title, message, priority="high", tags="", click=None):
    headers = {"Title": title, "Priority": priority}
    if tags:
        headers["Tags"] = tags
    if click:
        headers["Click"] = click
    req = urllib.request.Request(NTFY_URL, data=message.encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:
            resp.read()
    except Exception as e:
        log(f"ntfy notification failed: {e}")


def main():
    deadline = time.monotonic() + RUN_SECONDS
    consecutive_failures = 0
    blocked_alert_sent = False

    log(f"starting run: checking {BUY_URL} every {CHECK_INTERVAL}s")
    notify("Shoe checker cycle started",
           "Watching Kinetic Aura Slingback — Black/Sea Salt, size 9. "
           "You'll get a notification on every check where it's in stock.",
           priority="min", tags="eyes")
    warm_up()

    while time.monotonic() < deadline:
        try:
            available, stocklevel = check_stock()
            consecutive_failures = 0
            if available:
                log(f"IN STOCK (stocklevel={stocklevel}) — notifying")
                notify("IN STOCK: Black size 9!",
                       f"Kinetic Aura Slingback — Black/Sea Salt, size 9 is available "
                       f"(stock level: {stocklevel}). Tap to buy.",
                       priority="urgent", tags="tada,athletic_shoe", click=BUY_URL)
            else:
                log(f"not in stock (stocklevel={stocklevel})")
        except Exception as e:
            consecutive_failures += 1
            log(f"check failed ({consecutive_failures} in a row): {e}")
            # Bot-block or transient error: re-establish cookies before next try
            warm_up()
            if consecutive_failures >= BLOCKED_ALERT_THRESHOLD and not blocked_alert_sent:
                notify("Shoe checker is being blocked",
                       f"{consecutive_failures} consecutive checks have failed "
                       "(likely bot protection). The checker keeps retrying, but it is "
                       "currently blind. Check the GitHub Actions logs.",
                       priority="default", tags="warning")
                blocked_alert_sent = True

        remaining = deadline - time.monotonic()
        if remaining <= CHECK_INTERVAL:
            break
        time.sleep(CHECK_INTERVAL)

    log("run window finished; exiting (the schedule starts the next cycle)")


if __name__ == "__main__":
    sys.exit(main())
