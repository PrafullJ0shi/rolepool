"""Settings in one place. Every threshold used by a formula lives here and is quoted in the README."""
from __future__ import annotations

from pathlib import Path

BRAND = "Rolepool"
REPO_URL = "https://github.com/PrafullJ0shi/rolepool"
SITE_URL = "https://prafullj0shi.github.io/rolepool/"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "site"
CACHE = ROOT / ".http-cache"

USER_AGENT = (
    "RolepoolBot/0.1 (+https://github.com/PrafullJ0shi/rolepool; "
    "daily sweep of public job feeds; contact via GitHub issues)"
)

# Politeness
PER_HOST_RPS = 2.0          # requests per second per host
MAX_WORKERS = 8             # parallel hosts
TIMEOUT_S = 30.0
MAX_RETRIES = 3

# "New" window
NEW_WINDOW_DAYS = 3

# Hiring momentum
MOMENTUM_HALF_LIFE_DAYS = 7.0
MOMENTUM_MIN_BASE = 5        # floor on open roles in the rate denominator
MOMENTUM_SHRINK_K = 14       # sweeps of history before own-history z gets half weight
MOMENTUM_ASINH_SCALE = 0.01  # x = asinh(M / 0.01): tames the heavy right tail of M
Z_SCALE_FLOOR = 0.5          # minimum spread used in the cross-sectional z
H_TEMPER = 3.0               # H = 100 * tanh(z / 3)

# Freeze detector
FREEZE_NO_NEW_DAYS = 21
FREEZE_DROP_PCT = 0.30
COOLING_NO_NEW_DAYS = 10
HIRING_SCORE = 25
HIRING_MIN_NEW_7D = 2

# Freshness / ghost
FRESH_TAU_DAYS = 30.0
GHOST_AGE_MID = 60.0
GHOST_AGE_SCALE = 15.0
REPOST_LOOKBACK_DAYS = 90
CLOSED_KEEP_DAYS = 120

# Salary sanity bounds, USD per year
SALARY_MIN_USD = 8_000
SALARY_MAX_USD = 1_500_000

# Board relevance: general boards need this many crypto keyword points
RELEVANCE_MIN = 2
