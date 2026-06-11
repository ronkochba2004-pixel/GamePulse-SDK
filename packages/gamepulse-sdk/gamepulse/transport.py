from __future__ import annotations

import json as _json
import random
import time
from typing import Any

import httpx
from gamepulse_core.constants import API_KEY_HEADER, MAX_PAYLOAD_BYTES

from gamepulse.config import SDKConfig
from gamepulse.utils.logging import log


class Transport:
    """Synchronous HTTP transport with bounded retry + exponential backoff + jitter."""

    def __init__(self, cfg: SDKConfig) -> None:
        self.cfg = cfg
        self._client = httpx.Client(
            base_url=cfg.api_url,
            timeout=cfg.timeout_s,
            headers={API_KEY_HEADER: cfg.api_key or "", "Content-Type": "application/json"},
        )

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def post(self, path: str, json: dict[str, Any]) -> httpx.Response | None:
        if not self.cfg.api_key:
            return None
        body = _json.dumps(json).encode()
        if len(body) > MAX_PAYLOAD_BYTES:
            log.warning(
                "gamepulse: batch too large (%d bytes, limit %d) — dropping. "
                "Reduce batch_size or payload fields.",
                len(body),
                MAX_PAYLOAD_BYTES,
            )
            return None
        attempt = 0
        while True:
            attempt += 1
            try:
                log.debug("gamepulse: POST %s attempt=%d size=%d bytes", path, attempt, len(body))
                resp = self._client.post(path, content=body)
                log.debug("gamepulse: POST %s -> HTTP %d", path, resp.status_code)
                if resp.status_code < 500:
                    return resp
                log.warning("gamepulse: %s -> %s", path, resp.status_code)
            except httpx.HTTPError as e:
                log.warning("gamepulse: transport error %s: %s", path, e)

            if attempt >= self.cfg.max_retries:
                return None
            sleep = self.cfg.backoff_base_s * (2 ** (attempt - 1))
            sleep += random.uniform(0, sleep * 0.25)
            time.sleep(sleep)
