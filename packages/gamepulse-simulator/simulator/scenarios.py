from __future__ import annotations

import random
import time

import gamepulse

from simulator.personas import Persona

ITEMS = ["potion", "shield", "sword_upgrade", "extra_life", "speed_boost", "bomb"]
CURRENCIES = ["gold", "gems", "stars"]
IAP_SKUS = [
    ("starter_pack", 0.99),
    ("gem_bundle_100", 1.99),
    ("gem_bundle_500", 7.99),
    ("no_ads", 2.49),
    ("season_pass", 9.99),
]


def _earn_gold(amount: int) -> None:
    gamepulse.economy.earn(currency="gold", amount=amount, source=random.choice(["quest", "daily_bonus", "level_reward"]))


def play_session(player_id: str, persona: Persona) -> None:
    gamepulse.identify(player_id, persona=persona.name)
    duration = random.uniform(persona.session_min_s, persona.session_max_s)
    end_at = time.time() + duration

    # Occasional earn at session start
    if random.random() < 0.6:
        _earn_gold(random.randint(10, 50))

    # Whale IAP
    if persona.name == "whale" and random.random() < 0.15:
        sku, price = random.choice(IAP_SKUS)
        gamepulse.economy.purchase(sku=sku, price=price, currency="USD")
        gamepulse.economy.earn(currency="gems", amount=random.randint(50, 500), source="iap")

    with gamepulse.session():
        level = random.randint(1, 5)  # players pick up from a random level
        crashed = False

        while time.time() < end_at:
            gamepulse.progression.start(level=level)
            time.sleep(random.uniform(0.02, 0.15))

            if random.random() < persona.crash_chance:
                crashed = True
                gamepulse.track("error.crash", level=level, reason="sim_crash")
                break

            # Level complete or fail
            if random.random() < 0.65:
                stars = random.choices([1, 2, 3], weights=[0.3, 0.45, 0.25])[0]
                gamepulse.progression.complete(level=level, stars=stars)
                _earn_gold(level * 10 + stars * 5)

                # spend on powerup occasionally
                if random.random() < persona.spend_chance:
                    item = random.choice(ITEMS)
                    cost = random.randint(5, 30) * level
                    gamepulse.economy.spend(currency="gold", amount=cost, item=item)
            else:
                gamepulse.progression.fail(level=level, reason=random.choice(["time_out", "lives_exhausted", "gave_up"]))

            # Gameplay events
            if random.random() < 0.4:
                gamepulse.gameplay.action(name=random.choice(["jump", "attack", "dodge", "special"]))

            # Rage quit check (mid-session)
            if random.random() < persona.rage_quit_chance * 0.3:
                gamepulse.track("error.rage_quit", level=level)
                break

            level = min(level + 1, 20)

        if not crashed and random.random() < persona.rage_quit_chance * 0.7:
            gamepulse.track("error.rage_quit", level=level)
