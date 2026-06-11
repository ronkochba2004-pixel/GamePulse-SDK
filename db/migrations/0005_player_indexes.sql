-- 0005_player_indexes.sql — indexes to support Player Timeline and Retention queries
create index if not exists events_player_occurred_idx
  on gamepulse.events (player_id, occurred_at desc);

create index if not exists events_session_idx
  on gamepulse.events (session_id, occurred_at desc);

create index if not exists crashes_player_occurred_idx
  on gamepulse.crashes (player_id, occurred_at desc);
