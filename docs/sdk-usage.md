# SDK Quick Reference

Full documentation: [`packages/gamepulse-sdk/README.md`](../packages/gamepulse-sdk/README.md)

---

## Init

```python
import gamepulse

gamepulse.init(
    api_key="gpk_...",           # from Projects page
    project="my-game",           # project slug
    player_id="user_123",        # stable unique ID — see best practices
    api_url="https://gamepulse-api.onrender.com",  # or http://localhost:8000 for local dev
    app_version="1.0.0",         # optional
    enable_crash_capture=True,   # default True
    debug=False,                 # set True to log every event
)
```

Pass `api_key=None` for no-op mode (safe in tests — all calls silently disabled).

---

## Sessions

```python
with gamepulse.session():
    # gameplay here
    ...
# session_start and session_end sent automatically
```

---

## Identify

```python
gamepulse.identify("user_123", country="US", platform="PC", tier="free")
```

---

## Progression

```python
gamepulse.progression.start(level=5)
gamepulse.progression.complete(level=5, stars=3)
gamepulse.progression.fail(level=5, reason="lives_exhausted")
```

---

## Economy

```python
gamepulse.economy.earn(currency="gold", amount=100, source="level_reward")
gamepulse.economy.spend(currency="gold", amount=50, item="health_potion")
gamepulse.economy.purchase(sku="gem_bundle_500", price=7.99, currency="USD")
```

---

## Custom events

```python
gamepulse.track("tutorial.step_completed", step="movement", time_s=32)
gamepulse.track("feature.unlocked", feature="double_jump")
gamepulse.track("error.rage_quit", level=4)
```

---

## Flush / shutdown

```python
gamepulse.flush()     # send queued events immediately
gamepulse.shutdown()  # flush + stop background thread (call at process exit)
```

---

## Reliability and offline behaviour

### What the SDK guarantees today

| Mechanism | Status | Detail |
|-----------|--------|--------|
| In-memory event queue | ✅ Implemented | Bounded queue (default 10,000 events). Events are buffered here before the background flush thread sends them. |
| Batch uploads | ✅ Implemented | Events are sent in batches (default 50, max 500) via `POST /v1/events/batch`. |
| Retry on failure | ✅ Implemented | Up to 3 retries on 5xx responses or network errors. |
| Exponential backoff with jitter | ✅ Implemented | 0.5 s base, doubles each attempt, ±25% jitter. |
| Graceful shutdown flush | ✅ Implemented | `atexit` handler flushes the queue and ends the active session before the process exits. |
| Payload size enforcement | ✅ Implemented | Batches > 256 KB are dropped with a warning log before any network call. |
| Persistent offline storage | ✅ Implemented (opt-in) | Failed uploads are written to a JSONL store on disk and replayed on the next launch. Off by default; enable with `offline_storage=True`. |
| Crash persistence across restarts | ✅ Implemented (opt-in) | When `offline_storage=True`, a crash whose upload fails is saved to disk and re-sent on the next launch. |

### Persistent offline storage

By default the SDK keeps unsent events in memory only — fine for a stable
connection, but events are lost if the process exits while offline. Enable
**persistent offline storage** to survive API downtime and restarts:

```python
gamepulse.init(
    api_key="gpk_...",
    project="my-game",
    player_id="user_123",
    offline_storage=True,            # turn it on (default False)
    offline_storage_path=None,       # default: per-user app-data dir (see below)
    max_offline_events=10_000,       # cap on stored events (oldest dropped first)
    max_offline_bytes=5 * 1024 * 1024,  # 5 MB cap on each store file
)
```

**How it works**

```
event → in-memory queue → flush (batch upload)
                              ├─ 2xx  → done
                              ├─ 4xx  → permanent error, dropped (won't retry)
                              └─ network/5xx/offline → written to disk
next launch → load disk store → retry upload → delete only after a confirmed 2xx
```

- **Idempotent.** Persisted events reuse their original `event_id`, so the
  backend's `UNIQUE (project_id, event_id)` constraint dedupes any event that was
  actually received before the process died. No duplicate analytics.
- **Crashes too.** With offline storage on, a crash report that can't be sent at
  exit is saved and retried next launch — so a crash is not lost just because the
  network was down when it happened.
- **Bounded.** Each store file is capped by `max_offline_events` and
  `max_offline_bytes`; the oldest records are dropped first and a warning is
  logged.
- **Corruption-tolerant.** A damaged line in the store is skipped, never fatal.
- **Never raises.** All storage errors are caught and logged, consistent with the
  rest of the SDK.

**Where files are stored** (when `offline_storage_path=None`):

| OS | Default location |
|----|------------------|
| Windows | `%LOCALAPPDATA%\GamePulse\offline\` |
| macOS | `~/Library/Application Support/GamePulse/offline/` |
| Linux | `$XDG_DATA_HOME/gamepulse/offline/` (or `~/.local/share/gamepulse/offline/`) |

Two files are used: `events.jsonl` and `crashes.jsonl`.

### Remaining limitations

- **Hard kills lose in-flight events.** Only events that have already *failed a
  flush* are written to disk. Events still sitting in the in-memory queue when the
  process receives SIGKILL / OOM-kill (no chance to run the `atexit` flush) are
  lost. A normal exit flushes and persists them correctly. Write-through
  journaling of every event is intentionally out of scope for this MVP.
- **Crash duplicate edge case.** If a crash upload actually succeeds but the
  process dies before the store entry is removed, it will be re-sent next launch.
  Crashes have no server-side idempotency key, so this rare case can create one
  duplicate crash row. We favour *not losing* crashes over perfect dedup.

**Recommendation:** For critical telemetry (IAP purchases, level completions),
call `gamepulse.flush()` immediately after the event to minimise the window
where it could be lost.

```python
gamepulse.economy.purchase(sku="gem_bundle_500", price=7.99, currency="USD")
gamepulse.flush()  # send immediately — don't wait for the background flush
```

## Event taxonomy

| Category | Event type | Key payload fields |
|----------|-----------|-------------------|
| `system` | `session_start` | `platform` |
| `system` | `session_end` | `end_reason` |
| `progression` | `level_start` | `level` |
| `progression` | `level_complete` | `level`, `stars` |
| `progression` | `level_fail` | `level`, `reason` |
| `economy` | `currency_earn` | `currency`, `amount`, `source` |
| `economy` | `currency_spend` | `currency`, `amount`, `item` |
| `economy` | `iap_purchase` | `sku`, `price`, `currency` |
| `gameplay` | `action` | `name`, ... |
| `error` | `crash` | `level`, `reason` |
| `error` | `rage_quit` | `level` |
| `custom` | anything | arbitrary |
