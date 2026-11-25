"""The formula layer. Every function here is pure and has a test in tests/test_scoring.py.

1. Daily net-open rate        r_d = (O_d - C_d) / max(N_{d-1}, B)
2. Decayed momentum           M   = sum_d w_d r_d / sum_d w_d,  w_d = 2^(-age_d / h)
3. Hiring Momentum score      x = asinh(M / 0.01);  H = 100 * tanh(z / 3),  z = s*z_own + (1-s)*z_xs,  s = n / (n + K)
4. Freeze detector            FROZEN / COOLING / HIRING / STEADY / CHECK-BOARD (rules below)
5. Freshness                  F   = 100 * exp(-age / tau)
6. Ghost-job score            G   = 100 * (1 - prod_i (1 - p_i))
"""
from __future__ import annotations

import math
import re
import statistics
from datetime import date

from . import config


# ---------------------------------------------------------------- 1-2 momentum
def net_rate(opened: int, closed: int, prev_open: int, base: int = config.MOMENTUM_MIN_BASE) -> float:
    return (opened - closed) / max(prev_open, base)


def decayed_mean(values_by_age: list[tuple[int, float]], half_life: float = config.MOMENTUM_HALF_LIFE_DAYS) -> float:
    """values_by_age: (age in days, value). Weight 2^(-age/half_life)."""
    num = den = 0.0
    for age, v in values_by_age:
        w = 2.0 ** (-age / half_life)
        num += w * v
        den += w
    return num / den if den else 0.0


def momentum(daily: list[dict], today: date, window: int = 30) -> float:
    """daily: [{'date': date, 'opened': int, 'closed': int, 'prev_open': int}] for the last `window` days.
    Days with no row count as zero net change (they still carry weight)."""
    by_day = {d["date"]: d for d in daily}
    vals = []
    for age in range(window):
        d = date.fromordinal(today.toordinal() - age)
        row = by_day.get(d)
        r = net_rate(row["opened"], row["closed"], row["prev_open"]) if row else 0.0
        vals.append((age, r))
    return decayed_mean(vals)


# ---------------------------------------------------------------- 3 hiring momentum score
def stabilise(m: float, scale: float = config.MOMENTUM_ASINH_SCALE) -> float:
    """x = asinh(M / c). Linear near zero, logarithmic in the tail, defined for negative M."""
    return math.asinh(m / scale)


def robust_z(x: float, population: list[float], floor: float = config.Z_SCALE_FLOOR) -> float:
    """(x - median) / max(1.4826 * MAD, floor)."""
    if not population:
        return 0.0
    med = statistics.median(population)
    mad = statistics.median([abs(p - med) for p in population])
    return (x - med) / max(1.4826 * mad, floor)


def own_z(x: float, history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    mu = statistics.fmean(history)
    sd = statistics.pstdev(history)
    return (x - mu) / (sd + 0.05)


def hiring_score(m_today: float, own_history: list[float], cross_section: list[float],
                 k: int = config.MOMENTUM_SHRINK_K) -> dict:
    """All inputs are raw M values; they are stabilised here."""
    x = stabilise(m_today)
    n = len(own_history)
    s = n / (n + k)
    z_own = own_z(x, [stabilise(v) for v in own_history])
    z_xs = robust_z(x, [stabilise(v) for v in cross_section])
    z = s * z_own + (1 - s) * z_xs
    z = max(-6.0, min(6.0, z))
    return {"H": round(100 * math.tanh(z / config.H_TEMPER), 1), "z": round(z, 3), "z_own": round(z_own, 3),
            "z_xs": round(z_xs, 3), "shrink": round(s, 3)}


# ---------------------------------------------------------------- 4 freeze detector
def company_state(*, fetched_ok: bool, open_now: int, open_max_30d: int, no_new_days: int | None,
                  net_30d: int, new_7d: int, H: float, zero_streak: int = 0) -> str:
    if not fetched_ok:
        return "CHECK-BOARD"
    if open_now == 0:
        return "CHECK-BOARD" if (open_max_30d > 0 and zero_streak < 2) else "FROZEN"
    if no_new_days is not None:
        dropped = open_max_30d > 0 and open_now <= (1 - config.FREEZE_DROP_PCT) * open_max_30d
        if no_new_days >= config.FREEZE_NO_NEW_DAYS and (dropped or open_now == 0):
            return "FROZEN"
        if no_new_days >= 60:
            return "FROZEN"
    if H >= config.HIRING_SCORE and new_7d >= config.HIRING_MIN_NEW_7D:
        return "HIRING"
    if H <= -config.HIRING_SCORE or (net_30d < 0 and no_new_days is not None and no_new_days >= config.COOLING_NO_NEW_DAYS):
        return "COOLING"
    return "STEADY"


# ---------------------------------------------------------------- 5-6 freshness, ghost
_EVERGREEN = re.compile(r"general application|open application|talent (pool|community|network)|future (opportunit|role)|"
                        r"expression of interest|don.t see|not listed|spontaneous|always hiring|evergreen|join our talent", re.I)


def freshness(age_days: float, tau: float = config.FRESH_TAU_DAYS) -> float:
    return round(100 * math.exp(-max(age_days, 0) / tau), 1)


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def ghost_score(*, age_days: float, reposts: int, title: str, desc_len: int | None, company_state_: str) -> dict:
    p = {
        "age": 0.6 * _sigmoid((age_days - config.GHOST_AGE_MID) / config.GHOST_AGE_SCALE),
        "repost": min(0.5, 0.25 * reposts),
        "evergreen": 0.5 if _EVERGREEN.search(title or "") else 0.0,
        "thin": 0.15 if desc_len is not None and desc_len < 300 else 0.0,
        "company": {"FROZEN": 0.3, "COOLING": 0.15}.get(company_state_, 0.0),
    }
    keep = 1.0
    for v in p.values():
        keep *= 1 - v
    return {"G": round(100 * (1 - keep), 1), "parts": {k: round(v, 3) for k, v in p.items() if v}}


def ghost_band(g: float) -> str:
    return "low" if g < 25 else ("watch" if g < 50 else "likely stale")
