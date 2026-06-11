"""Persistent offline storage for unsent telemetry.

A small, dependency-free JSONL store that lets the SDK survive API downtime and
process restarts. Events/crashes that fail to upload are appended here and
replayed on the next launch.

Design goals (MVP, deliberately simple):
- **Best-effort, never raises.** Every public method swallows and logs its own
  errors so analytics never crashes the host game.
- **Corruption-tolerant.** A single malformed line is skipped, not fatal.
- **Bounded.** Per-file count and byte limits; oldest records are dropped first.
- **Idempotent-friendly.** Each record carries a stable ``id`` (the event_id for
  events) so replay reuses the original id and the backend's
  ``UNIQUE (project_id, event_id)`` constraint dedupes automatically.

Record format — one JSON object per line:

    {"id": "<stable-id>", "data": { ...wire payload... }}
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from pathlib import Path

from gamepulse.utils.logging import log

EVENTS_FILE = "events.jsonl"
CRASHES_FILE = "crashes.jsonl"


def default_storage_dir() -> Path:
    """Return a per-user application-data directory for offline telemetry."""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
        return root / "GamePulse" / "offline"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "GamePulse" / "offline"
    # Linux / other POSIX — follow XDG.
    base = os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "gamepulse" / "offline"


class OfflineStore:
    """Thread-safe JSONL-backed store for pending events and crashes."""

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        max_events: int = 10_000,
        max_bytes: int = 5 * 1024 * 1024,
    ) -> None:
        self.dir = Path(path) if path is not None else default_storage_dir()
        self.max_events = max_events
        self.max_bytes = max_bytes
        self._lock = threading.RLock()
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # pragma: no cover - filesystem edge
            log.warning("gamepulse: could not create offline dir %s: %s", self.dir, e)

    # ── paths ────────────────────────────────────────────────────────────────
    @property
    def events_path(self) -> Path:
        return self.dir / EVENTS_FILE

    @property
    def crashes_path(self) -> Path:
        return self.dir / CRASHES_FILE

    # ── public: events ───────────────────────────────────────────────────────
    def append_events(self, records: list[tuple[str, dict]]) -> None:
        self._append(self.events_path, records, max_count=self.max_events)

    def load_events(self) -> list[tuple[str, dict]]:
        return self._load(self.events_path)

    def remove_events(self, ids: set[str]) -> None:
        self._remove(self.events_path, ids)

    # ── public: crashes ──────────────────────────────────────────────────────
    def append_crashes(self, records: list[tuple[str, dict]]) -> None:
        # Crashes are high-value and low-volume; cap generously but still bound.
        self._append(self.crashes_path, records, max_count=self.max_events)

    def load_crashes(self) -> list[tuple[str, dict]]:
        return self._load(self.crashes_path)

    def remove_crashes(self, ids: set[str]) -> None:
        self._remove(self.crashes_path, ids)

    # ── internals ────────────────────────────────────────────────────────────
    def _append(
        self, file: Path, records: list[tuple[str, dict]], *, max_count: int
    ) -> None:
        if not records:
            return
        with self._lock:
            try:
                with file.open("a", encoding="utf-8") as fh:
                    for rec_id, data in records:
                        fh.write(json.dumps({"id": rec_id, "data": data}) + "\n")
            except Exception as e:
                log.warning("gamepulse: offline append failed (%s): %s", file.name, e)
                return
            self._enforce_limits(file, max_count)

    def _load(self, file: Path) -> list[tuple[str, dict]]:
        with self._lock:
            if not file.exists():
                return []
            out: list[tuple[str, dict]] = []
            seen: set[str] = set()
            try:
                text = file.read_text(encoding="utf-8")
            except Exception as e:
                log.warning("gamepulse: offline read failed (%s): %s", file.name, e)
                return []
            corrupt = 0
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    rec_id = obj["id"]
                    data = obj["data"]
                except Exception:
                    corrupt += 1
                    continue
                # De-dupe within the file, keeping the latest occurrence.
                if rec_id in seen:
                    out = [(i, d) for (i, d) in out if i != rec_id]
                seen.add(rec_id)
                out.append((rec_id, data))
            if corrupt:
                log.warning(
                    "gamepulse: skipped %d corrupt offline record(s) in %s",
                    corrupt,
                    file.name,
                )
            return out

    def _remove(self, file: Path, ids: set[str]) -> None:
        if not ids:
            return
        with self._lock:
            remaining = [(i, d) for (i, d) in self._load(file) if i not in ids]
            self._rewrite(file, remaining)

    def _enforce_limits(self, file: Path, max_count: int) -> None:
        """Drop oldest records until under both the count and byte limits."""
        try:
            records = self._load(file)
            over_count = len(records) - max_count
            dropped = 0
            if over_count > 0:
                records = records[over_count:]
                dropped += over_count
            # Byte limit — trim from the front until the file would fit.
            while records and self._encoded_size(records) > self.max_bytes:
                records.pop(0)
                dropped += 1
            if dropped:
                self._rewrite(file, records)
                log.warning(
                    "gamepulse: offline store %s over limit — dropped %d oldest record(s)",
                    file.name,
                    dropped,
                )
        except Exception as e:
            log.warning("gamepulse: offline limit enforcement failed (%s): %s", file.name, e)

    @staticmethod
    def _encoded_size(records: list[tuple[str, dict]]) -> int:
        return sum(
            len(json.dumps({"id": i, "data": d}).encode("utf-8")) + 1 for i, d in records
        )

    def _rewrite(self, file: Path, records: list[tuple[str, dict]]) -> None:
        """Atomically replace the file with exactly ``records`` (temp + os.replace)."""
        try:
            if not records:
                if file.exists():
                    file.unlink()
                return
            fd, tmp = tempfile.mkstemp(dir=str(self.dir), prefix=file.name, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    for rec_id, data in records:
                        fh.write(json.dumps({"id": rec_id, "data": data}) + "\n")
                os.replace(tmp, file)
            finally:
                if os.path.exists(tmp):
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
        except Exception as e:
            log.warning("gamepulse: offline rewrite failed (%s): %s", file.name, e)
