# Dashboard Guide

This guide walks through every page in the GamePulse dashboard and explains what it shows, how to read it, and when it's useful.

**Default URL:** `http://localhost:8501`

---

## Getting started

When you open the dashboard for the first time:

1. **Sign in** — create a free account with an email and password
2. **Create a project** — go to **Projects**, click "Create project", and give it a name and slug
3. **Copy your API key** — it is shown once on creation; save it
4. **Add the SDK to your game** — see the [SDK Integration Guide](../packages/gamepulse-sdk/README.md)
5. **Or generate demo data first** — go to **Simulation** and click "Run Average Simulation"

Once events are flowing, all pages populate automatically. There is no ETL step — queries run live against the database.

---

## Projects

**Sidebar position:** first page

The Projects page is where you manage your GamePulse projects.

- **Create a project** — each project is isolated: players, events, crashes, and economy data are scoped per project. Create one project per game title (or per environment: `my-game-dev`, `my-game-prod`).
- **Select a project** — clicking "Activate" on a project sets it as the active context for all other dashboard pages.
- **Copy your API key** — needed for `gamepulse.init()`. If you lose it, rotate it here.
- **Rotate key** — generates a new `gpk_...` key and immediately invalidates the old one.

> All other pages only show data for the **currently active project**.

---

## Overview

**What it shows:** Platform health at a glance.

### Metrics row

| Metric | What it means |
|--------|---------------|
| **Total sessions** | Number of sessions in the selected time window |
| **Avg session** | Average session length in seconds |
| **Crashes** | Number of crash events |
| **Rage quits** | Number of rage-quit events |
| **Crash-free rate** | Percentage of sessions with no crash — target is ≥ 99% |

### Charts

- **Daily Active Users** — unique players per day as an area chart. A sudden drop on a specific date usually means a bad build was shipped that day.
- **Sessions vs Crashes per Day** — grouped bar chart overlaying sessions, crashes, and rage quits. Lets you see whether crash volume is growing proportionally with sessions (expected) or disproportionately (a regression).
- **Day-by-day breakdown** — the same data in a table, useful for copy-pasting into a spreadsheet.

### Time window

Use the "Lookback days" filter in the sidebar to adjust the time window (default: last 7 days).

### When to use it

- **After every release** — check whether the crash-free rate dropped or DAU changed
- **Daily stand-up** — one-glance summary of platform health
- **Incident triage** — correlate a crash spike with a deployment date

---

## Players

**What it shows:** Who is playing your game.

### Metrics

- **Active players** — unique players seen in the time window
- **New players** — players whose `first_seen_at` falls within the window
- **Returning players** — active players who are not new

### Breakdowns

- **By country** — bar chart of player counts per country. Useful for prioritising localisation.
- **By platform** — iOS, Android, PC, Console, etc.
- **By app version** — shows which version of your game the active playerbase is running. Use this to decide when it's safe to drop support for an old version.

### Player timeline search

Enter any player ID to jump directly to that player's full event history (see **Player Timeline** below).

### When to use it

- **Before dropping an old app version** — check the percentage still on it
- **Localisation decisions** — see which regions are growing
- **Post-launch check** — confirm new installs are registering correctly

---

## Sessions

**What it shows:** How players spend time in your game.

### Metrics

- **Total sessions** — sessions in the window
- **Avg duration** — mean session length in seconds
- **Median duration** — less skewed by outliers than the mean

### Charts

- **Recent sessions table** — last 50 sessions with player ID, start time, duration, platform, and end reason
- **Duration histogram** — distribution of session lengths. A spike near zero means many players quit almost immediately (bad tutorial? crash on startup?). A long tail means you have engaged players.
- **End reason breakdown** — pie chart of `natural` / `crash` / `rage_quit`. A healthy game should be heavily weighted toward `natural`.

### When to use it

- **Tutorial analysis** — if the duration histogram shows a spike at 0–30 seconds, many players quit in the first 30 seconds
- **Crash impact** — see what fraction of sessions end in crashes
- **Rage quit spikes** — if rage quits increase after a level update, that level got too hard

---

## Funnels

**What it shows:** Level completion rates — how far players progress through your game.

### How to read the funnel

Each row represents one level. The pass rate is:

```
pass rate = level_complete events / level_start events
```

```
Level 1   ████████████████████  97%
Level 2   ████████████████████  91%
Level 3   █████████░░░░░░░░░░░  44%  ← difficulty spike
Level 4   ████████████████░░░░  78%
Level 5   ████████████████████  83%
```

### What to look for

- **Difficulty spikes** — a level with significantly lower pass rate than surrounding levels may need tuning
- **Gatekeeping levels** — very low pass rates on early levels block players from seeing later content
- **Tutorial effectiveness** — if level 1 pass rate is under 70%, the tutorial isn't working

### When to use it

- **After adding new levels** — verify the new levels have appropriate difficulty
- **After player feedback** — if players say the game is too hard, pinpoint which levels
- **Regular balance reviews** — set a baseline and check for drift

---

## Economy

**What it shows:** In-game economy flows and real-money purchases.

### Currency flows

Bar charts showing total earned vs. total spent per currency over time. A healthy economy should have a balance that motivates players to spend but not feel depleted.

### Top items

Which items are most purchased by spend volume and by frequency. High-frequency items are popular. High-volume items drive the most currency out of circulation.

### IAP revenue

- Total IAP revenue over time
- Revenue by SKU
- **Top spenders leaderboard** — your highest-value players by total IAP spend

### When to use it

- **Balancing earned currency** — if players are accumulating far more than they spend, rewards may be too generous
- **IAP conversion** — track which SKUs are actually selling
- **Whale identification** — the top spenders list lets you prioritise customer support for high-value players

---

## Crashes

**What it shows:** Errors grouped by fingerprint for easy prioritisation.

### Crash fingerprints

Crashes are grouped by `fingerprint = hash(exception_type + message)`. This means 500 instances of the same `NullPointerException: Level asset not found` appear as **one entry**, not 500. The count tells you how many sessions were affected.

### Columns

| Column | Meaning |
|--------|---------|
| **Fingerprint** | Short hash identifying this crash group |
| **Exception type** | e.g. `NullPointerException`, `OutOfMemoryError` |
| **Message** | First line of the exception message |
| **Affected sessions** | How many sessions hit this crash |
| **First seen** | When this crash first appeared (which build?) |
| **Last seen** | Whether it's still happening |
| **Severity** | `fatal`, `critical`, or `warning` |

### Stack trace viewer

Click a fingerprint row to expand the full stack trace for that crash group.

### When to use it

- **Immediately after a release** — check for new fingerprints that appeared with the new build
- **Triage meetings** — sort by "affected sessions" to fix the highest-impact bugs first
- **Regression tracking** — if a fingerprint's "last seen" date moves from weeks ago to today, a regression was introduced

---

## Live Events

**What it shows:** A real-time tail of the most recent events.

### Filters

- **Category** — filter to `progression`, `economy`, `error`, `gameplay`, `system`, or `custom`
- **Event type** — narrow to a specific event name within a category
- **Count** — show 50 to 1000 events (default 200)

The page auto-refreshes every 5 seconds when the auto-refresh toggle is enabled.

### When to use it

- **During SDK integration** — verify that your game is sending events correctly in real time
- **Live game sessions** — watch events appear as QA testers play
- **Debugging a specific player** — filter by player ID (if shown in the event payload) to trace exactly what happened

---

## Retention

**What it shows:** Cohort-based return rates — the most important long-term health metric for a game.

### How retention is measured

Players are grouped into cohorts by their **first play date**. For each cohort, the dashboard measures what percentage returned on Day 1, Day 3, Day 7, and Day 14.

```
Cohort (first play)    D1     D3     D7     D14
─────────────────────  ────   ────   ────   ────
2024-01-01             52%    31%    18%    11%
2024-01-02             48%    28%    15%    9%
2024-01-03             61%    38%    22%    14%
```

### Industry benchmarks (mobile games)

| Day | Good | Average | Poor |
|-----|------|---------|------|
| Day 1 | ≥ 40% | 25–40% | < 25% |
| Day 7 | ≥ 15% | 8–15% | < 8% |
| Day 14 | ≥ 10% | 5–10% | < 5% |

### When to use it

- **Measuring game quality** — long-term engagement is the single best indicator of whether your game is fun
- **After adding a feature** — did the new content improve Day 7 return rates for the cohort exposed to it?
- **Pre-launch checklist** — soft launch to a small market and check retention before global release

---

## Player Timeline

**What it shows:** The complete event history for a single player.

### How to use it

1. Enter any player external ID in the search box
2. The page shows every session this player has had, with:
   - Session duration and end reason
   - Every event within that session (chronological)
   - Economy transactions, level progressions, crashes

### When to use it

- **Support requests** — "I lost my progress" or "I was charged twice" — trace exactly what happened
- **Power-user analysis** — examine the sessions of your most engaged players to understand what makes them tick
- **Bug investigation** — a player reports a crash; find their ID in the Crashes page, then trace their full session here

---

## Settings

**What it shows:** Active project configuration and SDK quick-start snippet.

- API status (is the backend reachable?)
- Active project name, slug, and API key
- SDK code snippet pre-filled with your current project's API key
- The equivalent terminal simulator command
- GAMEPULSE_* environment variables currently set

### When to use it

- **Onboarding a new developer** — copy the pre-filled SDK snippet
- **Debugging connectivity** — the API status check tells you if the dashboard can reach the backend

---

## Simulation

**What it shows:** Demo data generator — for testing, demos, and exploring the dashboard before real players arrive.

> All data generated here is **fake**. It does not represent real players.

### Quick Simulation

Click **Run Average Simulation** to generate:
- 30 simulated players with mixed personas (casual, whale, rage-quitter, crasher)
- 1–3 sessions per player distributed across the past 7 days
- Level progression events, economy transactions, crashes, and rage quits
- Enough data to make all dashboard pages useful

### Custom Simulation

Adjust every parameter:

| Parameter | Description |
|-----------|-------------|
| **Players** | Number of fake players to create (1–200) |
| **Spread over days** | Distribute sessions across this many past days (default 7) |
| **Crash rate** | Percentage of sessions that end in a crash |
| **Rage quit rate** | Percentage of sessions that end in a rage quit |
| **Level fail rate** | Percentage of level attempts that fail |
| **Spend rate** | Percentage of completed levels where the player spends currency |
| **Persona mix** | Relative weight of casual / whale / rage-quitter / crasher players |

### After running

The results card shows exactly what was created (player count, session count, event count, crashes, rage quits, economy events). Navigate to any other dashboard page to explore the generated data.

### Why spread over days?

Data spread over 7+ past days produces time-series charts (DAU trends, retention cohorts) that are actually meaningful. Data generated all at once only populates a single day on the Overview chart.

---

## General tips

**Use the lookback filter.** Most pages have a sidebar "Lookback days" filter. Set it to 30 for a broad view or 1 for debugging today's events.

**Refresh after simulator runs.** Dashboard data is live — there is no manual refresh step. If you just ran the simulator and don't see data, make sure you're on the right project.

**Watch the crash-free rate.** Make it a habit to check Overview after every build. A drop from 99.5% to 97% after a release is a clear signal.

**Use Live Events during QA.** When you're testing a new feature, keep the Live Events page open. Seeing your events appear in real time confirms the SDK is wired up correctly.
