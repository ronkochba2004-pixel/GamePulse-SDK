-- 0003_crashes.sql — crash + error reports
create table if not exists gamepulse.crashes (
  id           bigserial primary key,
  project_id   uuid not null references gamepulse.projects(id) on delete cascade,
  player_id    uuid not null references gamepulse.players(id)  on delete cascade,
  session_id   uuid references gamepulse.sessions(id) on delete set null,
  fingerprint  text not null,
  exc_type     text not null,
  message      text,
  stacktrace   text not null,
  severity     text not null default 'error',
  platform     text,
  app_version  text,
  occurred_at  timestamptz not null,
  received_at  timestamptz not null default now(),
  context      jsonb not null default '{}'::jsonb
);
create index if not exists crashes_project_fp_occurred_idx
  on gamepulse.crashes (project_id, fingerprint, occurred_at desc);
create index if not exists crashes_project_occurred_idx
  on gamepulse.crashes (project_id, occurred_at desc);
