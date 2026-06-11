# gamepulse-core

Shared Pydantic models, enums, and schemas for the [GamePulse](https://github.com/ronkochba2004-pixel/GamePulse-SDK) analytics platform.

This package contains the wire-format types used by both the GamePulse API and the GamePulse Python SDK. It is an internal dependency — if you are integrating GamePulse into your game, install `gamepulse-sdk` instead.

```bash
pip install gamepulse-sdk
```

## Contents

- **`gamepulse_core.events`** — Pydantic event models (`BaseEvent`, `LevelStartEvent`, `CurrencySpendEvent`, …)
- **`gamepulse_core.schemas`** — HTTP request/response schemas (`BatchEventsRequest`, `SessionStartRequest`, …)
- **`gamepulse_core.enums`** — `EventCategory`, `Platform`, `SessionEndReason`, `Severity`
- **`gamepulse_core.constants`** — API header names, limits, flush defaults
- **`gamepulse_core.version`** — `__version__`, `SCHEMA_VERSION`

## Links

- [GitHub repository](https://github.com/ronkochba2004-pixel/GamePulse-SDK)
- [SDK package (gamepulse-sdk)](https://pypi.org/project/gamepulse-sdk/)
