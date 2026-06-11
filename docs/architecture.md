# GamePulse architecture

```
 SDK ──HTTPS──► FastAPI (ingest+query) ──► Supabase Postgres
                       ▲
                       └──── Streamlit dashboard (read-only via /v1/query)
 Simulator ─► SDK
```

- **packages/gamepulse-core** — Pydantic models, enums, schemas (single source of truth).
- **packages/gamepulse-sdk** — public `import gamepulse` API, background queue, retrying HTTP transport, crash hook.
- **packages/gamepulse-simulator** — thread-pool driver that runs the SDK as N synthetic players.
- **services/api** — FastAPI app with `/v1/events`, `/v1/sessions`, `/v1/crashes`, `/v1/players/identify`, `/v1/query/*`.
- **apps/dashboard** — Streamlit pages that call the query API.
- **db/migrations** — numbered SQL migrations applied to Supabase.

## Auth

- **SDK → API**: `X-GamePulse-Key` header; key is hashed (sha256) in `projects.api_key_hash`.
- **Dashboard → API**: Supabase JWT (HS256) verified against `SUPABASE_JWT_SECRET`.
- API process holds the **service role** key for Supabase.

## Idempotency

Each event carries a client-generated `event_id` UUID. The DB has
`UNIQUE (project_id, event_id)`, so retried batches are safe.

## Analytics aggregation

Dashboard pages that show DAU and session-level trends read from two materialized
views: `gamepulse.mv_dau` and `gamepulse.mv_session_stats`.

**Refresh mechanism** — the FastAPI process starts a daemon background thread
(`app/scheduler.py`) on startup that calls the Supabase RPC function
`public.gp_refresh_analytics_views()` (which wraps
`gamepulse.refresh_analytics_views()`) on a configurable interval.

| Setting | Env var | Default |
|---------|---------|---------|
| Refresh interval | `GAMEPULSE_ANALYTICS_REFRESH_INTERVAL_S` | 600 s (10 min) |

Set the env var to `0` to disable automatic refresh (useful in test environments).

**Staleness** — dashboard data can be up to `refresh_interval_s` seconds old.
Crash-free rate, session counts, and DAU figures are derived from the
materialized views. Raw event queries (Live Events, Player Timeline) always
read live rows.

**Limitations** — the scheduler is in-process and per-worker. With multiple
Uvicorn workers each worker refreshes independently (harmless but redundant).
For a production multi-worker setup, move the refresh job to a dedicated cron
worker or use `pg_cron` inside Postgres.

## Scaling notes

- `events` is indexed for time-range and type-range queries; ready for monthly partitioning via pg_partman.
- Read traffic for the dashboard goes through materialized views (`mv_dau`, `mv_session_stats`).
- The SDK transport is pluggable — swap HTTP for Kafka/SQS later without touching event types.
- All dashboard reads are via `/v1/query/*` — the storage engine can change to ClickHouse/BigQuery later.
