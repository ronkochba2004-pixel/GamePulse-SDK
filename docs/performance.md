# Performance & Complexity

This document consolidates the complexity and performance characteristics of
GamePulse and sets out the engineering considerations behind them. It complements
the per-component analysis in [SDK Architecture](sdk-architecture.md),
[Analytics Pipeline](analytics-pipeline.md), and [Database Design](database-design.md).

---

## Complexity summary

Notation: `N` = rows in a table, `k` = rows within a query window, `B` = batch size,
`P` = players, `D` = days in window, `L` = levels.

### Write path

| Operation | Time | Space | Where |
|---|---|---|---|
| SDK `track()` enqueue | O(1) | O(1) | `queue.py` |
| SDK batch flush | O(B) CPU + 1 request | O(B) | `queue.py` / `transport.py` |
| Player upsert | O(log N) | O(1) | `ingest_service.py` |
| Event batch insert (idempotent) | O(B log N) | O(B) | `events.py` (`ON CONFLICT DO NOTHING`) |
| Crash insert | O(log N) | O(L) | `crashes` repo |

### Read path (analytics)

| Metric | Time | Space |
|---|---|---|
| Overview | O(log N + k) | O(P + D) |
| Live Events (tail of n) | O(log N + n) | O(n) |
| Sessions analytics | O(log N + k log k) | O(k) |
| Players summary | O(log N + k) | O(k) |
| Progression funnel | O(log N + k) | O(P + L) |
| Economy summary | O(log N + k) | O(items) |
| Crash analytics | O(log N + k) | O(unique fingerprints) |
| Rage-quit analytics | O(log N + k + L log L) | O(L) |
| Retention cohort | O(log N + k·D) | O(P·D) |
| Player timeline | O(log N + n) | O(n) |

Every read leads with a `(project_id, <time> desc)` index, so the `log N` term is a
B-tree descent and the dominant cost is the `k` rows actually scanned within the
window. Scans are capped (50,000 events / 100,000 sessions) to bound worst-case
latency and memory.

### Simulation

| Aspect | Cost |
|---|---|
| Sessions generated | O(P · D · r) |
| Wall-clock time | ~O(D), parallelism capped at 64 workers |
| Memory | O(workers) + bounded SDK queue |

---

## Expected scaling behaviour

| Dimension | Behaviour | Limiting factor |
|---|---|---|
| Events/sec ingested | Linear until the single Uvicorn worker saturates | One worker + in-memory rate limiter (by design for the MVP) |
| Table growth | `events` is append-only; query cost depends on **window size**, not total rows, thanks to time-leading indexes | Needs monthly partitioning beyond ~10M rows |
| Concurrent dashboards | Each page issues a bounded scan; independent and cacheable | DB read throughput |
| Window width | Read cost grows with `k` (rows in window); retention grows with `k·D` | Scan caps; pre-aggregation for Overview |
| Players | Player-keyed indexes keep timeline/retention sub-linear in total players | Memory for `O(P·D)` retention sets |

The architecture is deliberately **vertically scalable first**: a single worker with
good indexes handles a small studio's traffic comfortably. The seams for horizontal
scale (Redis rate limiter, `pg_partman` partitioning, the swappable `/v1/query/*`
boundary) are documented in [Technical Debt & Roadmap](tech_debt.md).

---

## Performance Considerations

### Batching
The SDK buffers events in a bounded in-memory queue and flushes up to `batch_size`
(default 50, max 500) per request on a timer (`flush_interval_s`). Batching amortises
HTTP and TLS overhead across many events and turns N event calls into N/B requests,
which is the single biggest lever on ingest throughput.

### Retry logic
`Transport` retries only on network errors and 5xx, using bounded exponential
backoff with jitter (`0.5 · 2^(n-1)` plus up to 25% jitter, capped at
`max_retries`). 4xx responses are never retried — a malformed or unauthorised batch
cannot succeed on retry, so retrying would only waste work and delay the queue. The
jitter prevents thundering-herd retries when many clients recover from an outage
simultaneously.

### Offline persistence
Opt-in JSONL disk storage (`offline_storage=True`) journals batches that fail while
offline and replays them idempotently on the next launch (the original `event_id`
plus the DB's unique constraint guarantees no duplicates). The store is bounded by
count and bytes, dropping oldest-first, so it can never grow without limit. It is a
cold path — untouched while the network is healthy — which is why its `O(N)`
file-rewrite cost is acceptable.

### Event buffering and backpressure
The queue is bounded (`max_queue_size`, default 10,000). When full, `put_nowait`
drops the event with a warning rather than blocking the game thread. This is a
deliberate choice: analytics must never apply backpressure to gameplay. Sizing the
queue trades memory for resilience to flush stalls.

### Scheduled refreshes
The Overview materialized views are refreshed by an in-process daemon thread every
`GAMEPULSE_ANALYTICS_REFRESH_INTERVAL_S` seconds (default 600). This moves the cost
of DAU/session aggregation off the request path entirely — dashboard reads become an
indexed lookup of a few per-day rows. The trade-off is bounded staleness (up to one
refresh interval). Setting the interval to `0` disables the scheduler.

### Database indexing
Every hot query is backed by a composite, project-leading index (see
[Database Design](database-design.md)). Leading with `project_id` then a timestamp
lets one index serve the tenant filter, the time-range filter, and the sort order
simultaneously, so the planner can satisfy `WHERE project_id = ? AND occurred_at >= ?
ORDER BY occurred_at DESC LIMIT n` with a single index range scan and no sort step.

### Scalability considerations
- **Single worker by design.** The API runs one Uvicorn worker so the in-memory rate
  limiter and the refresh scheduler behave correctly; horizontal scale requires
  moving both to shared infrastructure (Redis, `pg_cron`).
- **Append-mostly tables.** No in-place updates on the hot path keeps index
  maintenance and vacuum pressure low.
- **Swappable storage boundary.** All dashboard reads go through `/v1/query/*`, so
  the storage engine can move to a columnar store without touching the SDK or UI.
- **Bounded everything.** Queue depth, batch size, payload size (256 KB), scan caps,
  and offline-store size are all bounded, giving predictable worst-case resource use.

See [Non-Functional Requirements](non-functional-requirements.md) for how these
considerations map to performance, scalability, and reliability targets.
