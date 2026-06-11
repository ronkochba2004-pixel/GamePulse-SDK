-- 0004_views_and_indexes.sql — analytics materialized views
drop materialized view if exists gamepulse.mv_dau;
create materialized view gamepulse.mv_dau as
  select project_id,
         date_trunc('day', started_at) as day,
         count(distinct player_id)     as dau
  from gamepulse.sessions
  group by 1, 2;
create index if not exists mv_dau_project_day_idx on gamepulse.mv_dau (project_id, day);

drop materialized view if exists gamepulse.mv_session_stats;
create materialized view gamepulse.mv_session_stats as
  select project_id,
         date_trunc('day', started_at) as day,
         count(*)                              as sessions,
         coalesce(avg(duration_s), 0)::int     as avg_duration_s,
         sum((end_reason = 'crash')::int)      as crashes,
         sum((end_reason = 'rage_quit')::int)  as rage_quits
  from gamepulse.sessions
  where ended_at is not null
  group by 1, 2;
create index if not exists mv_session_stats_project_day_idx
  on gamepulse.mv_session_stats (project_id, day);

-- helper to refresh both views
create or replace function gamepulse.refresh_analytics_views() returns void as $$
begin
  refresh materialized view gamepulse.mv_dau;
  refresh materialized view gamepulse.mv_session_stats;
end; $$ language plpgsql;
