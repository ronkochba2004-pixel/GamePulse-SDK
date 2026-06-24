"""GamePulse Demo Game — a tiny Tkinter control panel that drives the real SDK.

This is NOT a real game. It's a button board where every button calls an actual
GamePulse SDK function, so you can watch the dashboard update live while you
present. Look for the two clearly-marked sections below:

    1. GAMEPULSE SDK INITIALISATION   (where init() is called)
    2. EVENT HANDLERS                  (where each button tracks an event)

Run it with the workspace Python so `import gamepulse` resolves:

    uv run python examples/demo-game/demo_game.py

Configure it with three environment variables (or a .env file in the repo root):

    GAMEPULSE_API_URL       e.g. https://gamepulse-api.onrender.com
    GAMEPULSE_API_KEY       your project's gpk_... key (from the Projects page)
    GAMEPULSE_PROJECT_SLUG  your project slug
"""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
import uuid
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

import gamepulse
from gamepulse.client import get_client


# ──────────────────────────────────────────────────────────────────────────────
# Config — read from environment, with a friendly .env fallback
# ──────────────────────────────────────────────────────────────────────────────
def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a .env in the repo root or this folder.

    Deliberately tiny — no python-dotenv dependency. Existing environment
    variables always win, so an explicit `export` overrides the file.
    """
    here = Path(__file__).resolve()
    candidates = [here.parent / ".env", here.parents[2] / ".env"]
    for path in candidates:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config() -> dict[str, str]:
    _load_dotenv()
    return {
        "api_url": os.environ.get("GAMEPULSE_API_URL", "https://gamepulse-api.onrender.com"),
        "api_key": os.environ.get("GAMEPULSE_API_KEY", ""),
        "project": os.environ.get("GAMEPULSE_PROJECT_SLUG", ""),
        "dashboard_url": os.environ.get("GAMEPULSE_DASHBOARD_URL", "https://gamepulse-dashboard.onrender.com"),
    }


MISSING_CONFIG_MESSAGE = (
    "GamePulse is not configured.\n\n"
    "Set these environment variables (or put them in a .env file in the repo root):\n\n"
    "    GAMEPULSE_API_URL=https://gamepulse-api.onrender.com\n"
    "    GAMEPULSE_API_KEY=gpk_your_key_here\n"
    "    GAMEPULSE_PROJECT_SLUG=your-project-slug\n\n"
    "Get your API key from the dashboard:\n"
    "  Projects → (your project) → copy the gpk_... key.\n\n"
    "Then run this demo again."
)


# ──────────────────────────────────────────────────────────────────────────────
# The demo app
# ──────────────────────────────────────────────────────────────────────────────
class DemoGame:
    def __init__(self, root: tk.Tk, config: dict[str, str]) -> None:
        self.root = root
        self.config = config

        # Local "game state" — purely for the demo UI.
        self.player_id = f"demo_player_{uuid.uuid4().hex[:6]}"
        self.level = 1
        self.gold = 100
        self.session_active = False

        # ──────────────────────────────────────────────────────────────────────
        # 1. GAMEPULSE SDK INITIALISATION
        #    This is the single place a real game would call init(), once at
        #    startup, before any other SDK call.
        # ──────────────────────────────────────────────────────────────────────
        gamepulse.init(
            api_key=config["api_key"],
            project=config["project"],
            player_id=self.player_id,
            api_url=config["api_url"],
            app_version="demo-1.0.0",
            enable_crash_capture=False,  # we trigger crashes manually via a button
            debug=True,  # print SDK activity to the terminal so startup issues are visible
            on_send_error=self._on_sdk_error,  # surface HTTP failures in the event log
        )

        # Build the window first so it appears immediately, then fire identify
        # in the background. identify() makes a blocking HTTP call — calling it
        # here (before _build_ui / root.mainloop) would prevent the window from
        # appearing until the request completes or times out.
        self._build_ui()
        self._log(f"SDK initialised — sending to {config['api_url']} (project '{config['project']}').")
        self._log(f"You are player '{self.player_id}'. Press 'Start Session' to begin.")

        # Attach player attributes so the Players page shows country/platform.
        # Runs on a daemon thread — never blocks the UI.
        self._run_async(
            f"identify: player '{self.player_id}' registered",
            lambda: gamepulse.identify(self.player_id, country="US", platform="PC", tier="demo"),
        )

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        self.root.title("🎮 GamePulse Demo Game")
        self.root.geometry("720x720")
        self.root.minsize(640, 640)

        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="🎮 GamePulse Demo Game", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Every button calls the real GamePulse SDK. Press buttons, then watch the dashboard update live.",
            foreground="#555",
            wraplength=680,
        ).pack(anchor="w")

        # Live status strip
        status = ttk.Frame(self.root, padding=(16, 4))
        status.pack(fill="x")
        self.var_session = tk.StringVar()
        self.var_level = tk.StringVar()
        self.var_gold = tk.StringVar()
        self.var_player = tk.StringVar(value=self.player_id)
        for label, var in (
            ("Player", self.var_player),
            ("Session", self.var_session),
            ("Level", self.var_level),
            ("Gold", self.var_gold),
        ):
            cell = ttk.Frame(status)
            cell.pack(side="left", padx=(0, 24))
            ttk.Label(cell, text=label, foreground="#888", font=("Segoe UI", 8)).pack(anchor="w")
            ttk.Label(cell, textvariable=var, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self._refresh_status()

        ttk.Separator(self.root).pack(fill="x", padx=16, pady=8)

        # Button groups
        groups = ttk.Frame(self.root, padding=(16, 0))
        groups.pack(fill="x")

        self._button_group(groups, "Session", [
            ("▶ Start Session", self.on_start_session),
            ("⏹ End Session", self.on_end_session),
        ])
        self._button_group(groups, "Progression", [
            ("🎯 Start Level", self.on_start_level),
            ("✅ Complete Level", self.on_complete_level),
            ("❌ Fail Level", self.on_fail_level),
        ])
        self._button_group(groups, "Economy", [
            ("🪙 Earn Gold (+50)", self.on_earn_gold),
            ("🛒 Spend Gold (-25)", self.on_spend_gold),
            ("💳 Buy Gems ($4.99 IAP)", self.on_buy_iap),
        ])
        self._button_group(groups, "Errors & frustration", [
            ("💥 Trigger Crash", self.on_crash),
            ("😤 Trigger Rage Quit", self.on_rage_quit),
        ])
        self._button_group(groups, "Custom", [
            ("🔧 Send Custom Event", self.on_custom_event),
        ])

        # Event log
        log_frame = ttk.Frame(self.root, padding=(16, 8))
        log_frame.pack(fill="both", expand=True)
        ttk.Label(log_frame, text="Event log — what was sent to GamePulse", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.log = scrolledtext.ScrolledText(log_frame, height=10, font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        self.log.configure(state="disabled")

        # Footer
        footer = ttk.Frame(self.root, padding=(16, 8))
        footer.pack(fill="x")
        ttk.Button(footer, text="🌐 Open Dashboard", command=self.on_open_dashboard).pack(side="left")
        ttk.Label(
            footer,
            text="Tip: keep the dashboard open on Live Events while you click.",
            foreground="#888",
        ).pack(side="left", padx=12)

    def _button_group(self, parent: ttk.Frame, title: str, buttons: list[tuple]) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=8)
        frame.pack(fill="x", pady=4)
        for text, command in buttons:
            ttk.Button(frame, text=text, command=command, width=22).pack(side="left", padx=4)

    def _refresh_status(self) -> None:
        self.var_session.set("🟢 Active" if self.session_active else "⚪ Inactive")
        self.var_level.set(str(self.level))
        self.var_gold.set(f"{self.gold} 🪙")

    # ── Logging (thread-safe) ─────────────────────────────────────────────────
    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, self._append_log, f"[{ts}] {message}")

    def _append_log(self, line: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_sdk_error(self, description: str, count: int) -> None:
        """Called by the SDK (on the flush thread) when an HTTP send fails."""
        if count > 0:
            self._log(f"✗ send failed ({description}) — {count} event(s) dropped or queued for retry")
        else:
            self._log(f"✗ send failed ({description})")
        self._log("  Check terminal for details. Verify API key and that the API is running.")

    def _run_async(self, label: str, fn) -> None:
        """Run an SDK action off the UI thread, then flush so it appears live."""
        def worker() -> None:
            try:
                fn()
                gamepulse.flush()  # push immediately so the dashboard updates now
                self._log(f"✓ {label}")
            except Exception as exc:  # never let a demo click crash the UI
                self._log(f"✗ {label} — exception: {exc}")
        threading.Thread(target=worker, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────────
    # 2. EVENT HANDLERS — each one calls the real GamePulse SDK
    # ──────────────────────────────────────────────────────────────────────────
    def on_start_session(self) -> None:
        # → GamePulse: open a session (all later events attach to it)
        get_client().start_session()
        self.session_active = True
        self._refresh_status()
        self._run_async("▶ session started", lambda: None)

    def on_end_session(self) -> None:
        if not self.session_active:
            self._log("⚠ no active session — press 'Start Session' first")
            return
        # → GamePulse: close the session normally
        get_client().end_session(end_reason="normal")
        self.session_active = False
        self._refresh_status()
        self._run_async("⏹ session ended (normal)", lambda: None)

    def on_start_level(self) -> None:
        # → GamePulse: progression.start
        self._run_async(
            f"🎯 progression.start(level={self.level})",
            lambda: gamepulse.progression.start(level=self.level),
        )

    def on_complete_level(self) -> None:
        completed = self.level
        # → GamePulse: progression.complete
        self._run_async(
            f"✅ progression.complete(level={completed}, stars=3)",
            lambda: gamepulse.progression.complete(level=completed, stars=3),
        )
        self.level += 1  # advance to the next level
        self._refresh_status()

    def on_fail_level(self) -> None:
        # → GamePulse: progression.fail (level stays the same — player retries)
        self._run_async(
            f"❌ progression.fail(level={self.level}, reason='demo_fail')",
            lambda: gamepulse.progression.fail(level=self.level, reason="demo_fail"),
        )

    def on_earn_gold(self) -> None:
        self.gold += 50
        self._refresh_status()
        # → GamePulse: economy.earn
        self._run_async(
            "🪙 economy.earn(gold, +50)",
            lambda: gamepulse.economy.earn(currency="gold", amount=50, source="demo_reward"),
        )

    def on_spend_gold(self) -> None:
        if self.gold < 25:
            self._log("⚠ not enough gold to spend (need 25)")
            return
        self.gold -= 25
        self._refresh_status()
        # → GamePulse: economy.spend
        self._run_async(
            "🛒 economy.spend(gold, -25, item='health_potion')",
            lambda: gamepulse.economy.spend(currency="gold", amount=25, item="health_potion"),
        )

    def on_buy_iap(self) -> None:
        # → GamePulse: economy.purchase (real-money IAP → Economy revenue)
        self._run_async(
            "💳 economy.purchase(sku='gem_pack', $4.99)",
            lambda: gamepulse.economy.purchase(sku="gem_pack_500", price=4.99, currency="USD"),
        )

    def on_crash(self) -> None:
        # → GamePulse: report a crash. This is exactly what the SDK's automatic
        #   crash hook calls internally when an unhandled exception occurs.
        def report() -> None:
            get_client()._report_crash(  # noqa: SLF001 — the real internal crash path
                fingerprint="demo_crash_v1",
                exc_type="DemoCrashError",
                message="Simulated crash from the demo game",
                stacktrace=(
                    "Traceback (most recent call last):\n"
                    '  File "demo_game.py", line 1, in <module>\n'
                    "    raise DemoCrashError('boom')\n"
                    "DemoCrashError: boom"
                ),
                occurred_at=datetime.now(UTC),
            )
        self._run_async("💥 crash reported (see Crashes page)", report)

    def on_rage_quit(self) -> None:
        level = self.level
        # → GamePulse: a rage quit is both an explicit event AND a session that
        #   ends with the 'rage_quit' reason. Send both for the fullest signal.
        def rage() -> None:
            gamepulse.track("error.rage_quit", level=level)
            if self.session_active:
                get_client().end_session(end_reason="rage_quit")
        self._run_async(f"😤 rage quit at level {level} (see Rage Quits page)", rage)
        if self.session_active:
            self.session_active = False
            self._refresh_status()

    def on_custom_event(self) -> None:
        # → GamePulse: an arbitrary custom event
        self._run_async(
            "🔧 track('tutorial.step_completed', step='demo')",
            lambda: gamepulse.track("tutorial.step_completed", step="demo", source="demo_game"),
        )

    def on_open_dashboard(self) -> None:
        webbrowser.open(self.config["dashboard_url"])
        self._log(f"🌐 opened {self.config['dashboard_url']}")

    def shutdown(self) -> None:
        try:
            gamepulse.shutdown()  # flush remaining events + stop background thread
        finally:
            self.root.destroy()


def main() -> int:
    config = load_config()

    root = tk.Tk()
    if not config["api_key"] or not config["project"]:
        root.withdraw()
        messagebox.showerror("GamePulse Demo — not configured", MISSING_CONFIG_MESSAGE)
        root.destroy()
        return 1

    app = DemoGame(root, config)
    root.protocol("WM_DELETE_WINDOW", app.shutdown)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
