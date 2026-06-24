# Technical Debt & Phase 2 Roadmap

This document captures honest weak spots in the current MVP and what a proper
Phase 2 would look like.

---

## Current weak spots (honest audit)

### Database
| Item | Detail | Priority |
|------|--------|----------|
| No `events` partitioning | `events` is a single big table. Needs monthly partitioning via `pg_partman` before it grows past ~10M rows. | High for prod |
| Materialized views not auto-refreshed | **Implemented** — `mv_dau` / `mv_session_stats` are refreshed automatically every 10 min by the FastAPI scheduler (`app/scheduler.py`). Interval is configurable via `GAMEPULSE_ANALYTICS_REFRESH_INTERVAL_S`. | Done |
| No `player_timeline` index | `events` filtered by `player_id` will do a seq scan without an index. Add `CREATE INDEX ON gamepulse.events (player_id, occurred_at DESC)` | High |
| No `sessions` player index | `sessions` filtered by `player_id` for retention cohorts. Already has the index. | Done |

### API
| Item | Detail | Priority |
|------|--------|----------|
| In-memory rate limiter | Per-process, not shared. Fine for a single Uvicorn worker; breaks under horizontal scaling. Switch to Redis sliding-window. | Medium |
| Request body size limit | **Implemented** — `ContentSizeLimitMiddleware` enforces `MAX_PAYLOAD_BYTES` (256 KB) and returns HTTP 413. | Done |
| No API versioning strategy | `v1` prefix exists but there's no deprecation or multi-version routing. Add `X-API-Version` header handling. | Low |
| `resolve_project_from_api_key` hits DB on every request | Cache project lookups in Redis or an LRU with a TTL. Currently O(1 DB round-trip). | Medium at scale |
| Supabase client is synchronous | The `supabase-py` client is sync. All `await` calls are faked (they just call synchronously). Migrate to `asyncpg` directly for true async. | Phase 2 |

### SDK
| Item | Detail | Priority |
|------|--------|----------|
| Offline persistence | **Implemented (opt-in).** `offline_storage=True` enables a JSONL disk store (`gamepulse/storage.py`): failed uploads are persisted and replayed on next launch, idempotently via the original `event_id`. Bounded by `max_offline_events` / `max_offline_bytes`. **Residual gap:** events still in the in-memory queue at a hard kill (SIGKILL/OOM, no `atexit`) are not journaled — write-through is out of scope for the MVP. | Done (opt-in) |
| Crash persistence across restarts | **Implemented (opt-in).** With `offline_storage=True`, a crash whose upload fails at exit is saved and re-sent next launch. **Residual:** no server-side crash idempotency key, so a crash uploaded-but-not-acked before process death can produce one duplicate row on retry. | Done (opt-in) |
| Heartbeat not implemented | `Session` sends start/end but no periodic heartbeat to detect background/foreground transitions. | Phase 2 |
| No platform SDK | Only Python. A game engine SDK (Unity C#, Unreal C++) is the natural next step. | Phase 2 |

### Dashboard
| Item | Detail | Priority |
|------|--------|----------|
| No auth on query endpoints | `/v1/query/*` uses the same SDK API key as ingestion. Should be gated by Supabase JWT for multi-tenant dashboards. | Medium |
| No caching | Every page load fires a DB query. Add `@st.cache_data(ttl=60)` wrappers in `api_client.py`. | Easy win |
| Retention page imports inside function | `from lib.charts import line` inside page body — style inconsistency, not a bug. | Cosmetic |
| Player Timeline has no pagination | Event log truncated at 200. Add a `Load more` button. | Low |
| No real-time push | Live Events page short-polls. Use SSE or WebSocket for true streaming. | Phase 2 |

### Tests
| Item | Detail | Priority |
|------|--------|----------|
| Fake Supabase doesn't support `order(desc=True)` properly | The fake returns insertion order. For sorted queries this may differ from Supabase. Acceptable for unit tests, but note for e2e. | Low |
| No simulator test | No test exercises the simulator runner. Add a 5-second burst test. | Low |
| No mypy clean pass | `mypy` is run as `continue-on-error` in CI. Type errors exist in `conftest.py` (dynamic fake client) and dashboard files (no stubs for Streamlit). | Phase 2 |

---

## What a realistic Phase 2 looks like

### P2 core platform
- **True async DB**: Migrate to `asyncpg` + a schema migration tool (`alembic` or Supabase CLI migrations).
- **Event partitioning**: Monthly `events` partitions via `pg_partman`.
- **Redis**: For rate limiting, project-key caching, and future pub/sub.
- **Multi-tenant auth**: Supabase Auth JWT on `/v1/query/*`; `project_members` table.
- **Supabase Realtime**: Replace the Live Events short-poll with Supabase Realtime subscriptions in the dashboard.

### P2 SDK
- **Offline persistence**: Shipped as an opt-in JSONL disk store (see "Current weak spots → SDK"). Remaining P2 work: write-through journaling so the in-memory queue also survives hard kills, and a server-side crash idempotency key.
- **Heartbeat**: Session heartbeat every 60 s for accurate session length on crash.
- **Unity SDK (C#)**: Mirror of the Python SDK targeting game engines.

### P2 analytics
- **Cohort builder**: Flexible filter-based cohorts (not just day-of-first-session).
- **A/B test tracking**: `experiment_id` + `variant` fields on events.
- **Custom dashboards**: Drag-and-drop chart builder over the event schema.
- **Alerts**: Threshold-based alerts (crash rate > X%) → Slack/email.
- **Data export**: CSV/JSON export from the dashboard.

### P2 infrastructure
- **ClickHouse**: For events beyond ~100M rows; the `/v1/query/*` boundary makes this a swap.
- **Kafka**: Replace the SDK's direct HTTP flush with a Kafka producer; the API becomes a consumer.
- **GitHub Actions**: Add load tests (k6) and e2e tests against a staging Supabase project.
