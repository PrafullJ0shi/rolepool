"""USD reference rates from the European Central Bank via the free Frankfurter API (no key)."""
from __future__ import annotations

from .detect import FX_FALLBACK


def usd_rates(client) -> tuple[dict, str]:
    for url in ("https://api.frankfurter.dev/v1/latest", "https://api.frankfurter.app/latest"):
        data = client.get_json(url, {"base": "USD"})
        if data and data.get("rates"):
            rates = {"USD": 1.0, **{k: float(v) for k, v in data["rates"].items()}}
            for k, v in FX_FALLBACK.items():
                rates.setdefault(k, v)
            return rates, f"ECB {data.get('date')}"
    return dict(FX_FALLBACK), "fallback table"
