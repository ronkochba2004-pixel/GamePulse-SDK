from __future__ import annotations

import hashlib
import sys
import threading
import traceback
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gamepulse.client import GamePulseClient


def _fingerprint(exc_type: type[BaseException], tb: str) -> str:
    h = hashlib.sha1()
    h.update(exc_type.__name__.encode())
    for line in tb.splitlines():
        s = line.strip()
        if s.startswith("File ") or s.startswith("in "):
            h.update(s.encode())
    return h.hexdigest()


def install(client: GamePulseClient) -> None:
    prev_excepthook = sys.excepthook
    prev_thread_hook = getattr(threading, "excepthook", None)

    def _send(exc_type, exc, tb):
        try:
            stack = "".join(traceback.format_exception(exc_type, exc, tb))
            client._report_crash(  # noqa: SLF001
                fingerprint=_fingerprint(exc_type, stack),
                exc_type=exc_type.__name__,
                message=str(exc) if exc else None,
                stacktrace=stack,
                occurred_at=datetime.now(UTC),
            )
        except Exception:
            pass

    def _hook(exc_type, exc, tb):
        _send(exc_type, exc, tb)
        prev_excepthook(exc_type, exc, tb)

    def _thread_hook(args):
        _send(args.exc_type, args.exc_value, args.exc_traceback)
        if prev_thread_hook:
            prev_thread_hook(args)

    sys.excepthook = _hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _thread_hook
