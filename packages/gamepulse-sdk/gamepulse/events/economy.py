from __future__ import annotations

from typing import Any

from gamepulse.client import get_client


def earn(currency: str, amount: float, source: str | None = None, **extra: Any) -> None:
    get_client().track(
        "economy.currency_earn", currency=currency, amount=amount, source=source, **extra
    )


def spend(currency: str, amount: float, item: str | None = None, **extra: Any) -> None:
    get_client().track(
        "economy.currency_spend", currency=currency, amount=amount, item=item, **extra
    )


def purchase(sku: str, price: float, currency: str = "USD", **extra: Any) -> None:
    get_client().track(
        "economy.iap", sku=sku, price=price, currency=currency, **extra
    )
