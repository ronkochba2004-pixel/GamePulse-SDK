# 🎮 GamePulse Demo Game

A tiny Tkinter desktop app where **every button calls the real GamePulse SDK**.
Use it to demonstrate the whole platform live: press buttons here, watch the
dashboard light up.

It's not a real game — it's a control panel that fires real telemetry, so you
can show exactly how a game would integrate the SDK without building a game.

```
┌─────────────────────────────────────────┐
│ 🎮 GamePulse Demo Game                   │
│ Player: demo_player_a1b2c3               │
│ Session: 🟢 Active   Level: 3   Gold: 125│
│                                          │
│  Session   ▶ Start    ⏹ End             │
│  Progress  🎯 Start  ✅ Complete  ❌ Fail│
│  Economy   🪙 Earn   🛒 Spend   💳 IAP   │
│  Errors    💥 Crash  😤 Rage Quit        │
│  Custom    🔧 Send Custom Event          │
│                                          │
│  Event log…                              │
└─────────────────────────────────────────┘
```

---

## Where the SDK lives in the code

Open [`demo_game.py`](demo_game.py) — two sections are clearly marked:

1. **`GAMEPULSE SDK INITIALISATION`** — the single `gamepulse.init(...)` call.
2. **`EVENT HANDLERS`** — each button, with a `# → GamePulse:` comment showing
   the exact SDK call it makes.

| Button | SDK call | Dashboard page it updates |
|--------|----------|---------------------------|
| Start Session | `client.start_session()` | Sessions, Overview |
| End Session | `client.end_session("normal")` | Sessions |
| Start Level | `gamepulse.progression.start(level=N)` | Funnels |
| Complete Level | `gamepulse.progression.complete(level=N, stars=3)` | Funnels |
| Fail Level | `gamepulse.progression.fail(level=N, reason=…)` | Funnels |
| Earn Gold | `gamepulse.economy.earn("gold", 50, …)` | Economy |
| Spend Gold | `gamepulse.economy.spend("gold", 25, item=…)` | Economy |
| Buy Gems (IAP) | `gamepulse.economy.purchase(sku, 4.99, "USD")` | Economy (revenue) |
| Trigger Crash | `client._report_crash(…)` | Crashes |
| Trigger Rage Quit | `track("error.rage_quit", level=N)` + `end_session("rage_quit")` | Rage Quits, Sessions |
| Send Custom Event | `gamepulse.track("tutorial.step_completed", …)` | Live Events |

Every action also calls `gamepulse.flush()` so events reach the dashboard within
a second instead of waiting for the background flush.

---

## Full demo flow

### Option A — use the deployed platform (easiest)

The API and dashboard are already running at:

- **Dashboard:** https://gamepulse-dashboard.onrender.com
- **API:** https://gamepulse-api.onrender.com

Skip to step 3.

### Option B — run locally

#### 1. Start the API

```bash
make api
# or: uv run uvicorn app.main:app --reload --app-dir services/api --port 8000
```

#### 2. Start the dashboard

```bash
make dashboard
# or: uv run streamlit run apps/dashboard/Home.py
```

Open <http://localhost:8501>.

---

### 3. Create a project and copy its API key

In the dashboard: **Projects → Create project**. Copy the `gpk_...` key it
shows (also visible later under Projects → your project).

### 4. Configure the demo

Copy the template and fill in your key + slug:

```bash
cp examples/demo-game/.env.example .env       # in the repo root
```

**Deployed (default):**
```ini
GAMEPULSE_API_URL=https://gamepulse-api.onrender.com
GAMEPULSE_API_KEY=gpk_your_key_here
GAMEPULSE_PROJECT_SLUG=your-project-slug
GAMEPULSE_DASHBOARD_URL=https://gamepulse-dashboard.onrender.com
```

**Local development:**
```ini
GAMEPULSE_API_URL=http://localhost:8000
GAMEPULSE_API_KEY=gpk_your_key_here
GAMEPULSE_PROJECT_SLUG=your-project-slug
GAMEPULSE_DASHBOARD_URL=http://localhost:8501
```

(You can also `export` these as environment variables instead of using a file.)

### 5. Run the demo game

```bash
uv run python examples/demo-game/demo_game.py
```

> Run it with `uv run` (or any Python where the workspace is installed) so
> `import gamepulse` resolves. If the API key or slug is missing, the app shows a
> friendly dialog telling you what to set.

### 6. Press buttons

A good demo sequence:

1. **Start Session**
2. **Start Level → Complete Level** a few times (advances the level counter)
3. **Start Level → Fail Level** once or twice
4. **Earn Gold**, **Spend Gold**, **Buy Gems (IAP)**
5. **Send Custom Event**
6. **Trigger Crash**
7. **Trigger Rage Quit**
8. **End Session**

### 7. Watch the dashboard update live

| Press these | Then check this page |
|-------------|----------------------|
| Start/End Session | **Sessions**, **Overview** |
| Start/Complete/Fail Level | **Funnels** |
| Earn/Spend/Buy | **Economy** |
| Trigger Crash | **Crashes** |
| Trigger Rage Quit | **Rage Quits** |
| Any button | **Live Events** (real-time tail) |
| (any player activity) | **Player Timeline** — paste the player ID shown in the demo |

Click **🌐 Open Dashboard** in the demo to jump straight there. Keep **Live
Events** open while you click for the most immediate feedback.

---

## Notes

- **No extra dependencies.** Tkinter ships with Python; the demo only imports the
  GamePulse SDK from this workspace.
- **New player each run.** A fresh `demo_player_xxxxxx` ID is generated on
  startup (shown in the window). Re-run for a new player, e.g. to demonstrate
  new-vs-returning players or retention.
- **Crash capture is off** in the demo so the app's own UI errors aren't
  reported — the **Trigger Crash** button reports a crash explicitly instead.
- The window's close button calls `gamepulse.shutdown()` to flush any remaining
  events cleanly.
