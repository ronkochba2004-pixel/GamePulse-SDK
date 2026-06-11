import gamepulse


def test_noop_mode_never_raises():
    gamepulse.init(api_key=None, project="t", player_id="p1")
    gamepulse.track("custom.ping", value=1)
    gamepulse.progression.start(level=1)
    gamepulse.economy.spend(currency="gold", amount=5)
    gamepulse.flush()
    gamepulse.shutdown()
