# Non-Functional Requirements

This document states the non-functional requirements (NFRs) GamePulse is designed
to meet, the mechanisms that satisfy each, and the known limits of the current MVP.
It complements the functional behaviour documented in
[`docs/architecture.md`](architecture.md) and the analysis in
[Performance & Complexity](performance.md).

---

## 1. Performance

**Requirement.** Telemetry collection must add negligible overhead to the host game,
and dashboard queries must return interactively for a small studio's data volume.

| Mechanism | Effect |
|---|---|
| Non-blocking `track()` (O(1) enqueue) | The game thread never waits on analytics |
| Background batch flush | HTTP/TLS cost amortised across many events |
| Composite project-leading indexes | Hot queries are single index range scans |
| Materialized views for Overview | DAU/session trends served without a full scan |
| Bounded scans (50k events / 100k sessions) | Predictable worst-case query latency |

**Limits.** Live aggregation transfers up to the scan cap of rows per query; very
wide windows on large datasets should move to SQL `GROUP BY` or pre-aggregation.

---

## 2. Scalability

**Requirement.** The system should serve a small studio on free-tier infrastructure
and have a clear, low-risk path to larger scale.

| Mechanism | Effect |
|---|---|
| Append-mostly schema | Cheap inserts, low index-maintenance and vacuum pressure |
| Time-leading indexes | Query cost tracks window size, not total table size |
| Swappable `/v1/query/*` boundary | Storage engine can change without touching SDK/UI |
| Pluggable SDK transport | HTTP can be replaced by a queue (Kafka/SQS) later |

**Limits (by design for the MVP).** A single Uvicorn worker, an in-memory
per-process rate limiter, and an in-process refresh scheduler mean horizontal
scaling requires externalising rate limiting (Redis) and the refresh job
(`pg_cron`), and partitioning `events` (`pg_partman`) beyond ~10M rows. These are
documented in [Technical Debt & Roadmap](tech_debt.md).

---

## 3. Reliability

**Requirement.** Analytics must never crash or stall the host game, and telemetry
should survive transient network and backend failures.

| Mechanism | Effect |
|---|---|
| SDK never raises into user code | A failed send is logged, not thrown |
| Bounded retry with backoff + jitter | Rides out transient 5xx / network blips |
| Idempotent ingest (`event_id` + unique constraint) | Safe to retry any batch; no duplicate rows |
| Opt-in offline persistence | Events survive API downtime and process restarts |
| Bounded queue with drop-on-full | Analytics applies no backpressure to gameplay |
| `atexit` flush + graceful shutdown | Clean exits drain the queue and end the session |
| Health checks (`/healthz`, `/_stcore/health`) | Platform can detect and restart unhealthy services |

**Limits.** Events still in the in-memory queue at a hard kill (SIGKILL/OOM, no
`atexit`) are not journaled; a crash uploaded-but-not-acked before process death can
produce one duplicate (no server-side crash idempotency key yet).

---

## 4. Maintainability

**Requirement.** The codebase should be readable, testable, and safe to evolve.

| Mechanism | Effect |
|---|---|
| `gamepulse-core` single source of truth | Models/enums/schemas shared by SDK and API; no drift |
| Layered backend (api / services / repositories / db) | Clear separation of routing, logic, and storage |
| In-memory fake Supabase in tests | Full suite runs anywhere with zero infrastructure |
| Typed throughout + `py.typed` markers | Static analysis catches breakage early |
| Numbered, append-only SQL migrations | Schema history is explicit and reproducible |
| Documented complexity and decisions | New contributors can reason about cost and rationale |

**Limits.** `mypy` runs as `continue-on-error` in CI; the Supabase client is
synchronous (async calls are faked). Both are tracked for Phase 2.

---

## 5. Security

**Requirement.** Tenant data must be isolated, secrets protected, and the ingestion
surface hardened against abuse.

| Mechanism | Effect |
|---|---|
| Per-project API keys, stored as SHA-256 hash | Compromise of the DB does not reveal raw keys |
| Project scoping on every query | No query crosses tenant boundaries |
| Supabase JWT (HS256) for the dashboard | Dashboard auth separate from SDK ingest auth |
| Service-role key held only by the API process | Clients never receive privileged credentials |
| Per-key rate limiting | Caps abuse from a single key |
| Request body size limit (256 KB, HTTP 413) | Bounds memory and rejects oversized payloads |
| Secrets via environment, never committed | `.env` gitignored; Render secrets are `sync: false` |
| CORS restricted to the dashboard origin in production | Limits cross-origin access to the API |

**Limits.** `/v1/query/*` currently authenticates with the SDK API key rather than
the dashboard JWT, so query endpoints should be JWT-gated before multi-tenant public
exposure; the in-memory rate limiter is per-process. See
[Technical Debt & Roadmap](tech_debt.md).

---

## Summary

GamePulse prioritises **reliability and maintainability** (the SDK must be safe to
embed and the system safe to evolve) and meets **performance and security** targets
for its intended scale (a small studio on free-tier infrastructure). **Scalability**
is addressed by design at the architectural seams rather than fully implemented,
with each gap explicitly documented and given a concrete upgrade path.
