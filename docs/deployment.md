# Deployment Guide

## Recommended approach — Render Blueprint (both services, free tier)

`render.yaml` at the repo root defines both the API and the Dashboard as Render web
services. A single "Blueprint" deploy creates and configures both.

---

## Prerequisites

- A **GitHub repository** containing this code (must be public for Render free tier,
  or any visibility on a paid Render plan)
- A **Supabase project** with all migrations applied (`db/migrations/0001` → `0009`)
- Your Supabase project's **URL**, **service role key**, and **anon key** — all found
  in Supabase dashboard → Project Settings → API

---

## Step-by-step deployment

### 1. Push the repo to GitHub

```bash
git init          # if not already a git repo
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/gamepulse.git
git push -u origin main
```

### 2. Create a Render Blueprint

1. Go to [https://dashboard.render.com](https://dashboard.render.com)
2. Click **New → Blueprint**
3. Connect your GitHub account and select the repo
4. Render detects `render.yaml` and shows two services: `gamepulse-api` and `gamepulse-dashboard`
5. Click **Apply** — Render queues the first build for both services

### 3. Set secret environment variables

Both services have `sync: false` env vars that must be pasted manually.
Do this **before or immediately after** clicking Apply — builds will fail on startup
until the secrets are set.

In the Render dashboard, go to each service → **Environment** → **Add Secret File / Env Var**:

#### `gamepulse-api` — required secrets

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API → service_role key |
| `SUPABASE_JWT_SECRET` | Optional. Supabase → Project Settings → API → JWT Secret |

#### `gamepulse-dashboard` — required secrets

| Variable | Value |
|---|---|
| `SUPABASE_URL` | Same URL as above |
| `SUPABASE_ANON_KEY` | Supabase → Project Settings → API → anon / public key |
| `GAMEPULSE_DASHBOARD_API_URL` | **Set this in step 4 below** |

### 4. Set `GAMEPULSE_DASHBOARD_API_URL` after the API deploys

The dashboard needs the API's public URL, which Render only assigns after the first
successful build. The two-step process:

1. Wait for `gamepulse-api` to show **Live** in the Render dashboard
2. The API is deployed at: `https://gamepulse-api.onrender.com`
3. In Render: `gamepulse-dashboard` → **Environment** → set:
   ```
   GAMEPULSE_DASHBOARD_API_URL = https://gamepulse-api.onrender.com
   ```
4. Click **Save Changes** — Render automatically triggers a redeploy of the dashboard

### 5. Tighten CORS after both services are live

Once both services have permanent URLs, restrict the API to accept requests only from
the dashboard domain:

In Render: `gamepulse-api` → **Environment** → update:
```
GAMEPULSE_API_CORS_ORIGINS = https://gamepulse-dashboard.onrender.com
```

Save → Render redeploys the API automatically.

### 6. Prevent cold starts (optional but recommended)

Render free services spin down after 15 minutes of inactivity. The first request after
a quiet period takes ~30 seconds to wake the container.

Set up **UptimeRobot** (free) to ping both health endpoints every 14 minutes:
- `https://gamepulse-api.onrender.com/healthz`
- `https://gamepulse-dashboard.onrender.com/_stcore/health`

This keeps both services warm at zero cost.

---

## Supabase free tier behaviour

Supabase **pauses free projects** after 7 days of no database activity. When paused,
the API returns 500 on every request until you un-pause it from the Supabase dashboard
(Project Settings → General → Restore project).

Options:
- **Accept it** — un-pause manually before demos
- **Keep-alive query** — UptimeRobot can also POST to `/healthz` (which doesn't hit
  the DB), but you'd need a lightweight cron that queries the DB at least once a week
- **Supabase Pro ($25/mo)** — disables the pause entirely

---

## Environment variables — complete reference

### API service

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SUPABASE_URL` | **Yes** | — | `https://abc.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | — | **Server-only. Never expose to clients.** |
| `SUPABASE_JWT_SECRET` | No | — | Only needed if adding static JWT verification |
| `GAMEPULSE_ENV` | No | `dev` | Set to `production` for JSON logging |
| `GAMEPULSE_API_LOG_LEVEL` | No | `INFO` | |
| `GAMEPULSE_API_CORS_ORIGINS` | No | `*` | Comma-separated list of allowed origins |
| `GAMEPULSE_API_RATE_LIMIT_PER_MIN` | No | `600` | Per-API-key sliding window |
| `GAMEPULSE_ANALYTICS_REFRESH_INTERVAL_S` | No | `600` | MV refresh interval; `0` = off |
| `GAMEPULSE_API_HOST` | No | `0.0.0.0` | |
| `GAMEPULSE_API_PORT` | No | `8000` | |

### Dashboard service

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GAMEPULSE_DASHBOARD_API_URL` | **Yes** | `https://gamepulse-api.onrender.com` | Full `https://` URL of the API |
| `SUPABASE_URL` | **Yes** | — | Same as API |
| `SUPABASE_ANON_KEY` | **Yes** | — | Safe to expose; used for auth UI only |

---

## Alternative: Fly.io (API) + Render (Dashboard)

If you want the API always-on without cold starts and at no cost, deploy the API on
Fly.io's free tier (3 shared VMs, no sleep) and the dashboard on Render free.

`fly.toml` is already configured. After installing the Fly CLI:

```bash
fly auth login
fly launch --config fly.toml --name gamepulse-api --no-deploy
fly secrets set \
    SUPABASE_URL="https://abc.supabase.co" \
    SUPABASE_SERVICE_ROLE_KEY="eyJ..."
fly deploy
```

The API will be live at `https://gamepulse-api.fly.dev`.

Then deploy the dashboard on Render (Blueprint, one service only) and set
`GAMEPULSE_DASHBOARD_API_URL=https://gamepulse-api.fly.dev` (or `https://gamepulse-api.onrender.com` if you already have it there).

---

## Alternative: Railway

Railway auto-detects Dockerfiles. Add two services manually from the same repo:

| Service | Root directory | Dockerfile path |
|---|---|---|
| API | `.` | `services/api/Dockerfile` |
| Dashboard | `.` | `apps/dashboard/Dockerfile` |

Set all the same environment variables listed above in each service's Variables tab.
Railway's free tier ("Hobby") gives $5/month of credit and does not sleep services.

---

## Production checklist

- [ ] All `sync: false` env vars filled in for both services
- [ ] `GAMEPULSE_DASHBOARD_API_URL` set to the live API URL (with `https://`)
- [ ] `GAMEPULSE_API_CORS_ORIGINS` tightened to the dashboard domain
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is the **service role** key, not the anon key
- [ ] Supabase migrations `0001` → `0009` applied to the production Supabase project
- [ ] UptimeRobot (or similar) pinging both health endpoints every 14 minutes
- [ ] `GAMEPULSE_ENV=production` set on the API (enables JSON structured logging)
- [ ] Default API key `demo-key-please-rotate` rotated — go to Projects → Rotate Key
