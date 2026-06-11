-- 0009_refresh_fn_security_definer.sql
--
-- REFRESH MATERIALIZED VIEW requires superuser or ownership of the view.
-- The function previously ran as the calling role (Supabase's PostgREST/
-- service_role user), which owns nothing and cannot issue REFRESH.
--
-- SECURITY DEFINER causes the function to execute as its owner (postgres),
-- who created the views and can refresh them.
--
-- search_path is pinned to prevent search-path injection attacks, which is
-- mandatory best-practice for SECURITY DEFINER functions.
create or replace function gamepulse.refresh_analytics_views()
returns void
language plpgsql
security definer
set search_path = gamepulse
as $$
begin
  refresh materialized view gamepulse.mv_dau;
  refresh materialized view gamepulse.mv_session_stats;
end;
$$;

-- Ensure the service_role (used by the FastAPI scheduler) can call the function.
grant execute on function gamepulse.refresh_analytics_views() to service_role;
