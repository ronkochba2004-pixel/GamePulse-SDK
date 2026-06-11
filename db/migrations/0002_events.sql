-- 0002_events.sql — telemetry events
create table if not exists gamepulse.events (
  id           bigserial primary key,
  event_id     uuid not null,
  project_id   uuid not null references gamepulse.projects(id) on delete cascade,
  player_id    uuid not null references gamepulse.players(id)  on delete cascade,
  session_id   uuid references gamepulse.sessions(id) on delete set null,
  type         text not null,
  category     text not null,
  name         text not null,
  payload      jsonb not null default '{}'::jsonb,
  occurred_at  timestamptz not null,
  received_at  timestamptz not null default now(),
  sdk_version  text,
  unique (project_id, event_id)
);
create index if not exists events_project_occurred_idx
  on gamepulse.events (project_id, occurred_at desc);
create index if not exists events_project_type_occurred_idx
  on gamepulse.events (project_id, type, occurred_at desc);
create index if not exists events_payload_gin
  on gamepulse.events using gin (payload);
