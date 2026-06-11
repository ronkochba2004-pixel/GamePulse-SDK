-- Add owner_id (Supabase auth user UUID) and api_key (raw, for MVP display)
-- to gamepulse.projects, enabling per-user project management from the dashboard.
ALTER TABLE gamepulse.projects
  ADD COLUMN IF NOT EXISTS owner_id uuid,
  ADD COLUMN IF NOT EXISTS api_key  text;

-- Backfill demo project so the existing seed key remains visible.
UPDATE gamepulse.projects
  SET api_key = 'demo-key-please-rotate'
WHERE slug = 'demo' AND api_key IS NULL;

CREATE INDEX IF NOT EXISTS idx_projects_owner ON gamepulse.projects (owner_id);
