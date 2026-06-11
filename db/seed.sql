-- Seed a demo project. The plaintext API key is 'demo-key-please-rotate'.
-- Hash: sha256('demo-key-please-rotate')
insert into gamepulse.projects (name, slug, api_key_hash)
values (
  'Demo Game',
  'demo',
  encode(digest('demo-key-please-rotate', 'sha256'), 'hex')
)
on conflict (slug) do nothing;
