import math
from datetime import date

import pytest

from app import scoring


def test_net_rate_uses_floor():
    assert scoring.net_rate(3, 1, 2) == pytest.approx(2 / 5)
    assert scoring.net_rate(3, 1, 20) == pytest.approx(2 / 20)


def test_decayed_mean_half_life():
    # one value today, one 7 days old: weights 1 and 0.5
    assert scoring.decayed_mean([(0, 1.0), (7, 0.0)], half_life=7) == pytest.approx(1 / 1.5)


def test_momentum_counts_missing_days_as_zero():
    today = date(2026, 11, 25)
    m = scoring.momentum([{"date": today, "opened": 5, "closed": 0, "prev_open": 10}], today, window=30)
    w = [2 ** (-a / 7) for a in range(30)]
    assert m == pytest.approx(0.5 / sum(w))


def test_robust_z_and_floor():
    assert scoring.robust_z(5, [1, 2, 3, 4, 5]) == pytest.approx((5 - 3) / (1.4826 * 1))
    assert scoring.robust_z(2, [1, 1, 1]) == pytest.approx(1 / 0.5)  # zero MAD falls back to the floor
    assert scoring.robust_z(1, []) == 0.0


def test_stabilise_is_odd_and_compressive():
    assert scoring.stabilise(0) == 0
    assert scoring.stabilise(-0.05) == pytest.approx(-scoring.stabilise(0.05))
    assert scoring.stabilise(0.8) - scoring.stabilise(0.4) < scoring.stabilise(0.4) - scoring.stabilise(0.0)


def test_hiring_score_blends_with_shrinkage():
    xs = [0.0, 0.01, -0.01, 0.02, -0.02]
    first = scoring.hiring_score(0.05, [], xs)
    assert first["shrink"] == 0 and first["z"] == first["z_xs"]
    later = scoring.hiring_score(0.05, [0.0] * 7 + [0.01] * 7, xs)
    assert later["shrink"] == pytest.approx(0.5)
    assert later["z"] == pytest.approx(0.5 * later["z_own"] + 0.5 * later["z_xs"], abs=1e-3)
    assert -100 <= later["H"] <= 100
    assert scoring.hiring_score(1e9, [], xs)["H"] == pytest.approx(100 * math.tanh(6 / 3), abs=0.1)  # z clipped at 6
    assert scoring.hiring_score(0.0, [], [0.0, 0.0, 0.0])["H"] == 0


@pytest.mark.parametrize("kw,state", [
    (dict(fetched_ok=False, open_now=5, open_max_30d=5, no_new_days=1, net_30d=0, new_7d=0, H=0), "CHECK-BOARD"),
    (dict(fetched_ok=True, open_now=0, open_max_30d=8, no_new_days=3, net_30d=-8, new_7d=0, H=-50, zero_streak=1), "CHECK-BOARD"),
    (dict(fetched_ok=True, open_now=0, open_max_30d=8, no_new_days=30, net_30d=-8, new_7d=0, H=-50, zero_streak=2), "FROZEN"),
    (dict(fetched_ok=True, open_now=6, open_max_30d=10, no_new_days=25, net_30d=-4, new_7d=0, H=-30), "FROZEN"),
    (dict(fetched_ok=True, open_now=9, open_max_30d=10, no_new_days=25, net_30d=-1, new_7d=0, H=-10), "COOLING"),
    (dict(fetched_ok=True, open_now=9, open_max_30d=9, no_new_days=70, net_30d=0, new_7d=0, H=0), "FROZEN"),
    (dict(fetched_ok=True, open_now=20, open_max_30d=20, no_new_days=0, net_30d=10, new_7d=6, H=60), "HIRING"),
    (dict(fetched_ok=True, open_now=20, open_max_30d=20, no_new_days=0, net_30d=10, new_7d=1, H=60), "STEADY"),
    (dict(fetched_ok=True, open_now=20, open_max_30d=20, no_new_days=None, net_30d=0, new_7d=0, H=0), "STEADY"),
    (dict(fetched_ok=True, open_now=0, open_max_30d=0, no_new_days=None, net_30d=0, new_7d=0, H=0), "FROZEN"),
])
def test_company_state(kw, state):
    assert scoring.company_state(**kw) == state


def test_freshness():
    assert scoring.freshness(0) == 100
    assert scoring.freshness(30) == pytest.approx(100 / math.e, abs=0.1)


def test_ghost_score_combines_independent_signals():
    young = scoring.ghost_score(age_days=1, reposts=0, title="Backend Engineer", desc_len=3000, company_state_="STEADY")
    assert young["G"] < 5
    old_repost = scoring.ghost_score(age_days=120, reposts=2, title="Backend Engineer", desc_len=3000, company_state_="FROZEN")
    p = [0.6 / (1 + math.exp(-(120 - 60) / 15)), 0.5, 0.3]
    expected = 100 * (1 - (1 - p[0]) * (1 - p[1]) * (1 - p[2]))
    assert old_repost["G"] == pytest.approx(expected, abs=0.1)
    assert scoring.ghost_band(old_repost["G"]) == "likely stale"
    pool = scoring.ghost_score(age_days=1, reposts=0, title="General Application - Talent Pool", desc_len=None, company_state_="STEADY")
    assert pool["parts"]["evergreen"] == 0.5
