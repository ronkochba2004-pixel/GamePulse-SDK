# Database

Numbered SQL migrations for the Supabase Postgres instance. Apply in order via the
Supabase SQL editor, `psql`, or the Supabase CLI.

```bash
for f in db/migrations/*.sql; do
  psql "$SUPABASE_DB_URL" -f "$f"
done
psql "$SUPABASE_DB_URL" -f db/seed.sql
```

Schema lives in the `gamepulse` namespace. All ingestion uses the **service role** key
from the API; the dashboard never talks to Postgres directly.

Materialized views (`mv_dau`, `mv_session_stats`) should be refreshed periodically:

```sql
select gamepulse.refresh_analytics_views();
```

(Schedule via `pg_cron` every 5 min in production.)
