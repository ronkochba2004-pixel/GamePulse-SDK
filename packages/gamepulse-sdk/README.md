# GamePulse Python SDK

**Game analytics for indie and small-team studios.** Track player sessions, progression, economy, crashes, and custom events — then explore live dashboards without writing a single query.

```python
import gamepulse

gamepulse.init(api_key="gpk_...", project="my-game", player_id="user_42")

with gamepulse.session():
    gamepulse.progression.start(level=3)
    gamepulse.economy.spend(currency="gold", amount=50, item="health_potion")
    gamepulse.progression.complete(level=3, stars=2)
```

---

## Table of contents

1. [What is GamePulse?](#1-what-is-gamepulse)
2. [Installation](#2-installation)
3. [Getting your API key](#3-getting-your-api-key)
4. [Initializing the SDK](#4-initializing-the-sdk)
5. [Sessions](#5-sessions)
6. [Identifying players](#6-identifying-players)
7. [Progression events](#7-progression-events)
8. [Economy events](#8-economy-events)
9. [Custom events](#9-custom-events)
10. [Crash reporting](#10-crash-reporting)
11. [Testing without a network](#11-testing-without-a-network)
12. [Best practices](#12-best-practices)
13. [Full integration example](#13-full-integration-example)
14. [Understanding your dashboard](#14-understanding-your-dashboard)
15. [Generating demo data](#15-generating-demo-data)
16. [Design notes](#16-design-notes)

---

## 1. What is GamePulse?

GamePulse is a **self-hosted game analytics platform**. You deploy the backend once, integrate this SDK into your game, and get a live analytics dashboard showing:

- **Who** is playing — breakdown by country, platform, and app version
- **How far** players get — level completion funnel with pass/fail rates per level
- **What** they spend — in-game currency flows, item popularity, IAP revenue
- **When and why** they leave — session end reasons, rage quits, crashes with stack traces
- **Whether they return** — Day 1, Day 3, Day 7, and Day 14 retention cohorts

Unlike Firebase or Unity Analytics, **you own all the data** — no vendor lock-in, no data leaving your infrastructure. Unlike building from scratch, you get working dashboards on day one.

---

## 2. Installation

```bash
pip install gamepulse-sdk
```

> **Self-hosted:** GamePulse requires a running API server and a Supabase (Postgres) database.  
> If your team has already set up GamePulse, they will give you an `api_key` and `api_url`.  
> To run the full stack yourself, see the [developer setup guide](../../README.md#quickstart-10-minutes).

---

## 3. Getting your API key

1. Open the GamePulse dashboard (default: `http://localhost:8501`)
2. Sign in or create an account
3. Go to **Projects → Create project**
4. Give your project a name and a slug (e.g. `my-platformer`)
5. Copy the API key shown — it starts with `gpk_` and is only displayed once

Your key looks like:

```
gpk_A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6
```

To retrieve it again later, go to **Projects** in the dashboard and click your project.

---

## 4. Initializing the SDK

Call `gamepulse.init()` **once at startup**, before any other SDK calls.

```python
import gamepulse

gamepulse.init(
    api_key="gpk_your_key_here",      # from the Projects page
    project="my-platformer",          # your project's slug
    player_id="user_abc123",          # unique ID for this player (see note below)
    api_url="http://localhost:8000",  # your GamePulse API server URL
    app_version="1.0.0",              # optional — shown in the Players breakdown
    enable_crash_capture=True,        # optional — auto-report unhandled exceptions
)
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `api_key` | Yes | — | Your project's SDK key (`gpk_...`) |
| `project` | Yes | — | Your project slug (e.g. `my-platformer`) |
| `player_id` | Yes | — | A stable, unique identifier for this player |
| `api_url` | Yes | — | Base URL of your GamePulse API (no trailing slash) |
| `app_version` | No | `"unknown"` | Version string shown in the Players dashboard |
| `enable_crash_capture` | No | `True` | Hook `sys.excepthook` to auto-send unhandled exceptions |
| `offline_storage` | No | `False` | Persist failed uploads to disk and replay them next launch (see [§10.5](#105-offline-storage-surviving-downtime-and-restarts)) |
| `offline_storage_path` | No | `None` | Directory for the offline store; `None` uses a per-user app-data dir |
| `max_offline_events` | No | `10000` | Max events kept on disk; oldest dropped first |
| `max_offline_bytes` | No | `5 MB` | Max size of each offline store file |
| `debug` | No | `False` | Log every event dispatch to the `gamepulse` logger |

### Choosing a player ID

Use a **stable, permanent** identifier that does not change between sessions. Good options:

```python
# Option A — generate a UUID on first run and persist it locally
from pathlib import Path
import uuid

id_file = Path.home() / ".mygame" / "player_id"
id_file.parent.mkdir(exist_ok=True)
if not id_file.exists():
    id_file.write_text(str(uuid.uuid4()))
player_id = id_file.read_text().strip()

# Option B — use your auth system's user ID
player_id = auth.current_user.id

# Option C — device fingerprint (if available)
player_id = platform.get_device_id()
```

**Avoid:** randomly generated IDs created fresh each run, email addresses (PII), or IP addresses. A changing player ID splits one real player into dozens of ghost players in the dashboard.

---

## 5. Sessions

A **session** represents one uninterrupted play period — from when the player launches the game or re-enters gameplay, to when they stop.

Wrap each play session in `gamepulse.session()`:

```python
with gamepulse.session():
    # All your gameplay code here
    run_game_loop()
# Session ends automatically when the `with` block exits
```

The context manager automatically:
- Sends a `session_start` event when entered
- Sends a `session_end` event with a reason when the block exits
- Records `end_reason = "crash"` if the block exits via an unhandled exception

### Session end reasons

| Reason | When it is recorded |
|--------|---------------------|
| `natural` | Player exits normally (menu, quit button, closed window) |
| `crash` | An unhandled exception propagates out of the `with` block |
| `rage_quit` | You emit a `error.rage_quit` event (see below) |

### Detecting rage quits

```python
with gamepulse.session():
    result = run_game_loop()

    if result == "rage_quit":
        # Record the rage quit before the session closes
        gamepulse.track("error.rage_quit", level=current_level)
```

The Sessions dashboard shows the ratio of natural, crash, and rage-quit endings so you can spot if a particular update made players frustrated.

---

## 6. Identifying players

Use `gamepulse.identify()` to attach attributes to a player. Call it after `init()` and again any time attributes change (e.g. after the player logs in or changes settings).

```python
gamepulse.identify(
    "user_abc123",          # must match the player_id used in init()
    country="US",           # shown in the Players map/breakdown
    platform="PC",          # shown in the platform chart
    tier="premium",         # any custom attributes you want
    level_reached=12,
)
```

`country` and `platform` are first-class fields with dedicated charts in the dashboard. All other keyword arguments are stored as a JSON blob and visible on the Player Timeline page.

---

## 7. Progression events

Track level starts, completions, and failures. These feed the **Funnels** page, which shows pass/fail rates per level and makes difficulty spikes immediately visible.

```python
# Player enters a level
gamepulse.progression.start(level=5)

# Player completes it (stars are optional)
gamepulse.progression.complete(level=5, stars=3)

# Player fails
gamepulse.progression.fail(
    level=5,
    reason="lives_exhausted",  # or "time_out", "gave_up", or any string
)
```

Always emit `start` before `complete` or `fail`. The funnel is built by counting starts vs. completions per level number.

### What the funnel looks like

```
Level 1  ████████████████████  97% pass
Level 2  ████████████████████  91% pass
Level 3  █████████░░░░░░░░░░░  44% pass  ← spike — worth investigating
Level 4  ████████████████░░░░  78% pass
Level 5  ████████████████████  83% pass
```

A sudden drop like level 3 above is a signal to review the level's difficulty, tutorial, or tutorial gaps.

---

## 8. Economy events

Track in-game currency and real-money purchases. These feed the **Economy** page.

### Earning currency

```python
gamepulse.economy.earn(
    currency="gold",
    amount=100,
    source="level_reward",   # "quest", "daily_bonus", "achievement", "iap", etc.
)
```

### Spending currency

```python
gamepulse.economy.spend(
    currency="gold",
    amount=50,
    item="health_potion",    # the item or feature purchased
)
```

### Real-money purchases (IAP)

```python
gamepulse.economy.purchase(
    sku="gem_bundle_500",
    price=7.99,
    currency="USD",
)
```

You can track multiple currencies simultaneously (`gold`, `gems`, `energy`, etc.). The Economy dashboard shows:
- Net flow per currency (earned vs. spent)
- Top items by spend frequency
- IAP revenue over time
- A leaderboard of your highest-spending players

---

## 9. Custom events

Track anything not covered by the built-in event types. Use the `category.event_name` naming convention.

```python
# Tutorial
gamepulse.track("tutorial.step_completed", step="movement_controls", time_s=32)
gamepulse.track("tutorial.skipped", at_step="weapons_intro")

# Feature usage
gamepulse.track("feature.unlocked", feature="double_jump", at_level=3)
gamepulse.track("feature.used", feature="map_view")

# A/B test
gamepulse.track("experiment.enrolled", experiment="shop_ui", variant="B")

# Player action
gamepulse.track("settings.changed", setting="difficulty", value="hard")
gamepulse.track("social.friend_invited", method="share_link")
```

Custom events appear live on the **Live Events** page and can be filtered by category. Payloads can contain any JSON-serialisable values.

---

## 10. Crash reporting

### Automatic (default)

When `enable_crash_capture=True` (the default), the SDK installs hooks on `sys.excepthook` and `threading.excepthook`. Any unhandled exception is caught, serialised with a full stack trace, and sent to the backend automatically.

```python
gamepulse.init(..., enable_crash_capture=True)  # this is the default

# Any unhandled exception is reported automatically:
def load_assets():
    raise FileNotFoundError("assets/level_12.bundle not found")
```

### Manual / caught exceptions

To report a caught exception — for example, a non-fatal error you want to monitor:

```python
try:
    result = network.fetch_leaderboard()
except TimeoutError as e:
    gamepulse.track(
        "error.network_timeout",
        endpoint="leaderboard",
        error=str(e),
        retry_count=3,
    )
    show_cached_leaderboard()  # graceful fallback
```

### What the Crashes page shows

- Crashes **grouped by fingerprint** (exception type + message hash) — so 500 identical crashes appear as one entry, not 500
- Full **stack traces** for each fingerprint
- **Affected session count** and first/last seen timestamps
- **Severity** breakdown (fatal, critical, warning)

This makes it easy to prioritise: fix the crash affecting 200 sessions before the one affecting 3.

### 10.5 Offline storage: surviving downtime and restarts

By default the SDK holds unsent events in memory. That's fine on a stable
connection, but if the player has no internet — or the game closes before the
queue is flushed — those events are lost.

Enable **persistent offline storage** to keep telemetry safe across API downtime
and process restarts:

```python
gamepulse.init(
    api_key="gpk_...",
    project="my-game",
    player_id="user_123",
    offline_storage=True,   # opt in
)
```

**What it does**

1. Every event first goes through the in-memory queue and a normal batch upload.
2. If the upload fails because the network is down or the server is unreachable,
   the events are written to a small JSONL file on disk.
3. On the next launch, the SDK loads the file, retries the upload, and **deletes
   each record only after the backend confirms it** (HTTP 2xx).

Crash reports get the same treatment — if a crash can't be sent at exit, it's
saved and re-sent next launch, so you don't lose the crash that mattered most.

**It won't create duplicates.** Persisted events keep their original event ID, and
the backend enforces `UNIQUE (project_id, event_id)`. An event that was actually
received before the process died is deduplicated automatically on replay.

**It won't grow without bound.** Each store file is capped (`max_offline_events`,
`max_offline_bytes`); the oldest records are dropped first, with a warning logged.

**It won't crash your game.** A corrupted record is skipped, and every storage
error is caught and logged — never raised.

**Where the files live** (when `offline_storage_path` is not set):

| OS | Location |
|----|----------|
| Windows | `%LOCALAPPDATA%\GamePulse\offline\` |
| macOS | `~/Library/Application Support/GamePulse/offline/` |
| Linux | `$XDG_DATA_HOME/gamepulse/offline/` (or `~/.local/share/gamepulse/offline/`) |

**Limitation:** only events that have already *failed an upload attempt* are
written to disk. Events still waiting in the in-memory queue when the process is
hard-killed (SIGKILL/OOM, where the exit flush can't run) are not recovered. A
normal shutdown flushes and persists them correctly. For critical events, call
`gamepulse.flush()` right after emitting them.

---

## 11. Testing without a network

Pass `api_key=None` to put the SDK into **no-op mode**. Every call becomes a silent no-op — no network requests, no background threads, no errors.

```python
import gamepulse
import os

gamepulse.init(
    api_key=os.getenv("GAMEPULSE_KEY"),  # set to None in your test environment
    project="my-game",
    player_id="test_player",
    api_url="http://localhost:8000",
)

# Safe to call in tests — all no-ops when api_key is None
with gamepulse.session():
    gamepulse.progression.start(level=1)
    gamepulse.progression.complete(level=1, stars=3)
```

No mocking, no patching, no teardown needed. Just leave `GAMEPULSE_KEY` unset in your CI environment.

---

## 12. Best practices

### Use consistent, stable player IDs

```python
# Good — stable UUID persisted to disk
player_id = load_or_create_player_id()

# Bad — different every run
player_id = str(uuid.uuid4())  # generates a new ID each launch
```

A changing player ID fractures one real player into many disconnected records. Retention cohorts, the player timeline, and economy summaries all break.

### Always wrap gameplay in a session

```python
# Good — events are linked to a session record
with gamepulse.session():
    gamepulse.progression.start(level=1)

# Also valid, but events float unattached in the event stream
gamepulse.track("menu.opened")
```

### Don't track every frame

The SDK batches events, but sending thousands per second wastes resources and fills the queue. Track **state changes**, not continuous values.

```python
# Don't — floods the queue
while game_running:
    gamepulse.track("player.pos", x=player.x, y=player.y)  # ~60/sec

# Do — track meaningful transitions
on_checkpoint_reached:
    gamepulse.track("level.checkpoint", level=3, checkpoint_id=2)

on_enemy_killed:
    gamepulse.track("combat.kill", enemy_type="boss", weapon="sword")
```

### Call `shutdown()` at process exit

```python
try:
    run_game()
finally:
    gamepulse.shutdown()  # flushes remaining events and stops the background thread
```

The SDK registers an `atexit` handler automatically, but some environments (particularly Windows services and embedded Python runtimes) skip `atexit`. An explicit call is the safest pattern.

### Use `identify()` after account actions

```python
# At login or account creation — associate metadata with the player
gamepulse.identify(player_id, country=get_country(), tier="free")

# After IAP — update their tier
gamepulse.identify(player_id, tier="premium")
```

### Keep event names consistent

Choose a naming convention and stick to it across your entire codebase.

```python
# Good — consistent category.verb_noun pattern
gamepulse.track("tutorial.step_completed", ...)
gamepulse.track("tutorial.step_skipped", ...)
gamepulse.track("shop.item_viewed", ...)
gamepulse.track("shop.item_purchased", ...)

# Bad — inconsistent naming makes filtering harder
gamepulse.track("TutorialComplete", ...)
gamepulse.track("tutorial_skip", ...)
gamepulse.track("shopView", ...)
```

---

## 13. Full integration example

A realistic integration for a level-based platformer:

```python
# analytics.py — initialise once, import anywhere
import os
import uuid
from pathlib import Path

import gamepulse


def _get_player_id() -> str:
    """Return a stable, persistent player UUID."""
    id_file = Path.home() / ".my_platformer" / "player_id"
    id_file.parent.mkdir(parents=True, exist_ok=True)
    if not id_file.exists():
        id_file.write_text(str(uuid.uuid4()))
    return id_file.read_text().strip()


def init_analytics(app_version: str, country: str, platform: str) -> None:
    player_id = _get_player_id()

    gamepulse.init(
        api_key=os.getenv("GAMEPULSE_API_KEY"),
        project=os.getenv("GAMEPULSE_PROJECT", "my-platformer"),
        player_id=player_id,
        api_url=os.getenv("GAMEPULSE_API_URL", "http://localhost:8000"),
        app_version=app_version,
        enable_crash_capture=True,
    )

    # Attach player attributes so the dashboard can break down by country/platform
    gamepulse.identify(player_id, country=country, platform=platform)
```

```python
# main.py — game entry point
from analytics import init_analytics
import gamepulse


def run_game() -> None:
    init_analytics(
        app_version="2.1.0",
        country=detect_country(),
        platform=detect_platform(),
    )

    player = load_save_file()

    while player.wants_to_play():
        with gamepulse.session():
            level = player.current_level

            while True:
                # ── Level start ─────────────────────────────────────────────
                gamepulse.progression.start(level=level)

                result = play_level(level)

                # ── Level complete ──────────────────────────────────────────
                if result.won:
                    stars = result.stars  # 1, 2, or 3
                    gamepulse.progression.complete(level=level, stars=stars)

                    reward = level * 50 + stars * 10
                    gamepulse.economy.earn(
                        currency="coins", amount=reward, source="level_reward"
                    )

                    if result.used_hint:
                        gamepulse.economy.spend(
                            currency="coins", amount=20, item="hint"
                        )

                    level += 1

                # ── Level fail ──────────────────────────────────────────────
                elif result.failed:
                    gamepulse.progression.fail(
                        level=level,
                        reason=result.fail_reason,  # "time_out", "lives_exhausted", etc.
                    )

                    if not player.wants_retry():
                        break  # exits session naturally

                # ── Rage quit ───────────────────────────────────────────────
                elif result.quit:
                    gamepulse.track("error.rage_quit", level=level)
                    break

                # ── IAP ─────────────────────────────────────────────────────
                if player.just_purchased_iap():
                    sku, price = player.last_iap
                    gamepulse.economy.purchase(sku=sku, price=price, currency="USD")

    gamepulse.shutdown()


if __name__ == "__main__":
    run_game()
```

---

## 14. Understanding your dashboard

Once events are flowing, the dashboard at `http://localhost:8501` (default) gives you these pages:

### Overview
Platform-wide health at a glance. Shows Daily Active Users as an area chart, sessions vs. crashes per day as a bar chart, crash-free rate (target: ≥ 99%), and total sessions and avg session length.

**Use it to:** spot regressions after a release — a crash spike or DAU drop on a specific day usually points to a bad build.

### Players
Active players broken down by country, platform, and app version. Shows which version of your game the playerbase is actually running, and which markets are most active.

**Use it to:** decide when it's safe to drop support for an old app version, or which regions need localisation.

### Sessions
Recent sessions list, session duration histogram, and a pie chart of end reasons (natural / crash / rage quit). A healthy game has mostly "natural" sessions; a large crash or rage-quit slice indicates a problem.

**Use it to:** track whether a patch reduced crashes, or whether a hard level is causing rage quits.

### Funnels
Level completion funnel showing the pass rate for each level. A sudden drop in pass rate is a difficulty spike — players are hitting a wall and not progressing.

**Use it to:** identify levels that need to be tuned (too hard, too confusing, or bugged).

### Economy
Currency earned vs. spent over time, top items by spend volume, IAP revenue chart, and a leaderboard of your highest-spending players (whales).

**Use it to:** balance your in-game economy, see which items are popular, and identify spenders who might churn.

### Crashes
Top crash fingerprints (grouped by exception type + message), ranked by affected session count. Click a fingerprint to see the full stack trace, severity, and when it was first/last seen.

**Use it to:** prioritise which bugs to fix — fix the crash hitting 400 sessions before the one hitting 2.

### Live Events
A real-time tail of the most recent events, filterable by category (progression, economy, error, gameplay, custom). Refreshes automatically.

**Use it to:** verify your SDK integration is working correctly — you should see events appearing within seconds of gameplay.

### Retention
Cohort-based return rates: of players who first played on a given day, what percentage came back on Day 1, Day 3, Day 7, and Day 14?

**Use it to:** measure whether your game is engaging enough to keep players returning. Industry benchmarks: Day 1 ≥ 40%, Day 7 ≥ 15%.

### Player Timeline
Per-player event history. Enter any player ID to see their full session history, every level they played, every item they bought, and every crash they experienced.

**Use it to:** debug specific player reports, understand power-user journeys, or investigate suspicious activity.

For a more detailed walkthrough of each page, see [`docs/dashboard-guide.md`](../../docs/dashboard-guide.md).

---

## 15. Generating demo data

Before you have real players, use the **Simulation** page to populate the dashboard with realistic fake data.

### From the dashboard (recommended)

1. Go to **Simulation** in the sidebar
2. Click **Run Average Simulation**
   - Creates 30 fake players spread across the past 7 days
   - Includes crashes, rage quits, economy events, and level progression
3. Explore any other dashboard page — it will be fully populated

For custom scenarios (high crash rate, whale-heavy cohort, etc.), use the **Custom Simulation** tab.

### From the terminal

```bash
python -m simulator \
    --players 50 \
    --duration 120 \
    --api-url http://localhost:8000 \
    --api-key gpk_your_key_here \
    --project my-game
```

| Flag | Description |
|------|-------------|
| `--players` | Number of concurrent fake players |
| `--duration` | How long to run (seconds) |
| `--api-url` | Your GamePulse API server URL |
| `--api-key` | Your project's SDK key |
| `--project` | Your project slug |

---

## 16. Design notes

These are not things you need to configure — just things worth knowing about how the SDK works.

**Never raises in user code.** All SDK errors are caught, logged to the `gamepulse` logger, and swallowed. Your game will never crash because of an analytics failure.

**Non-blocking.** Calls like `progression.start()` return immediately. Events are placed on an in-memory queue and flushed by a background thread (default: every 2 seconds, or in batches of 50).

**Retry with backoff.** Failed uploads are retried up to 3 times with exponential backoff and jitter before giving up.

**Idempotent delivery.** Each event carries a client-generated UUID. The backend stores events with a `UNIQUE (project_id, event_id)` constraint, so retried batches never create duplicates.

**Optional offline durability.** With `offline_storage=True`, uploads that fail are persisted to disk and replayed on the next launch (see [§10.5](#105-offline-storage-surviving-downtime-and-restarts)).

**Manual flush.** Call `gamepulse.flush()` to flush the queue immediately — useful before a scheduled restart or a long idle period.

```python
gamepulse.flush()    # sends all queued events now
gamepulse.shutdown() # flush + stop background thread
```
