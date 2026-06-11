from __future__ import annotations

import concurrent.futures as futures
import time
import uuid

import gamepulse

from simulator import personas, scenarios


def run(players: int, duration_s: int, api_url: str, api_key: str, project: str) -> None:
    gamepulse.init(
        api_key=api_key,
        project=project,
        api_url=api_url,
        player_id=None,  # set per-session via identify()
        enable_crash_capture=False,  # sim creates synthetic crashes
    )
    deadline = time.time() + duration_s
    print(f"[sim] {players} players for {duration_s}s -> {api_url}")

    def worker(i: int) -> int:
        persona = personas.pick()
        pid = f"sim_player_{i:05d}_{uuid.uuid4().hex[:6]}"
        n = 0
        while time.time() < deadline:
            scenarios.play_session(pid, persona)
            n += 1
        return n

    with futures.ThreadPoolExecutor(max_workers=min(players, 64)) as ex:
        results = list(ex.map(worker, range(players)))

    gamepulse.flush()
    gamepulse.shutdown()
    print(f"[sim] done. sessions per player: {results}")
