# Shoe stock checker

Watches [sorel.com](https://www.sorel.com/p/kinetic-aura-slingback-womens-sandal-2151361.html)
for the **Kinetic™ Aura Slingback Women's Sandal** in **Black/Sea Salt (color 010), size 9**
and pushes a phone notification every time a check finds it in stock.

## How it works

- A GitHub Actions workflow starts every 6 hours (`0 */6 * * *` UTC). A concurrency
  group cancels the previous run when a new one starts, so exactly one checker is
  alive at a time.
- Each run executes [check_shoes.py](check_shoes.py), which loops for ~5h45m
  (just under GitHub's 6-hour job limit), checking Sorel's Product-Variation JSON
  endpoint every **2 minutes**.
- On every check where the shoe is available, it POSTs to **https://ntfy.sh/mayada-shoes**
  with an urgent-priority notification and a tap-to-buy link.
- It stays silent unless the shoe is in stock. The one exception: if ~an hour of
  consecutive checks fail (bot-blocked), it sends a single warning per cycle so it
  never fails silently.

## Subscribe to notifications

Install the [ntfy app](https://ntfy.sh/) (iOS/Android) and subscribe to the topic:

```
mayada-shoes
```

Note: ntfy.sh topics are public — anyone who knows the topic name can subscribe or post.

## Stopping it

Delete this repository, or disable the workflow under **Actions → Shoe stock checker →
"…" → Disable workflow**.

## Caveats

- GitHub automatically disables scheduled workflows after **60 days without repo
  activity** — GitHub emails a warning; push any commit or re-enable it to keep it going.
- Scheduled runs can start late when GitHub is busy, so there can be short gaps
  between 6-hour cycles.
- Sorel uses PerimeterX bot protection. The script establishes cookies like a browser
  and retries, but if GitHub's IPs get hard-blocked the checker will notify you that
  it's blind rather than fail silently.
