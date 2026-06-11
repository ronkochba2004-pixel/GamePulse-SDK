-- 0001_init.sql — projects, players, sessions
create schema if not exists gamepulse;
create extension if not exists "pgcrypto";

create table if not exists gamepulse.projects (
  id           uuid primary key default gen_random_uuid(),
  name         text not null,
  slug         text not null unique,
  api_key_hash text not null,
  created_at   timestamptz not null default now()
);

create table if not exists gamepulse.players (
  id            uuid primary key default gen_random_uuid(),
  project_id    uuid not null references gamepulse.projects(id) on delete cascade,
  external_id   text not null,
  first_seen_at timestamptz not null default now(),
  last_seen_at  timestamptz not null default now(),
  country       text,
  platform      text,
  app_version   text,
  attributes    jsonb not null default '{}'::jsonb,
  unique (project_id, external_id)
);
create index if not exists players_project_last_seen_idx
  on gamepulse.players (project_id, last_seen_at desc);

create table if not exists gamepulse.sessions (
  id            uuid primary key default gen_random_uuid(),
  project_id    uuid not null references gamepulse.projects(id) on delete cascade,
  player_id     uuid not null references gamepulse.players(id)  on delete cascade,
  started_at    timestamptz not null,
  ended_at      timestamptz,
  duration_s    integer generated always as
                  (case when ended_at is null then null
                        else extract(epoch from (ended_at - started_at))::int end) stored,
  end_reason    text,
  platform      text,
  app_version   text,
  device        jsonb not null default '{}'::jsonb
);
create index if not exists sessions_project_started_idx
  on gamepulse.sessions (project_id, started_at desc);
create index if not exists sessions_player_started_idx
  on gamepulse.sessions (player_id, started_at desc);
