"""State across sweeps: first seen, last seen, closes, reposts, and the opened/closed diff."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import config


def parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_diff(state: dict, jobs: list[dict], ok_sources: set[str], now: datetime, baseline_sources: set[str]):
    """Update `state` in place.

    state[key] = {first_seen, last_seen, closed_at, reposts, opened_at, baseline, source, company, title}
    - a key present now and open before: last_seen = now
    - a key present now and closed before: reopened; reposts += 1 if it closed within REPOST_LOOKBACK_DAYS
    - a key open before, absent now, and its source fetched OK: closed_at = now
    - absent now but its source failed: left open (stale), never counted as a close
    Returns (opened_keys, closed_keys, reopened_keys).
    """
    now_s = iso(now)
    present = set()
    opened, reopened = [], []
    for j in jobs:
        k = j["key"]
        present.add(k)
        s = state.get(k)
        posted = parse_ts(j.get("posted_at"))
        if s is None:
            baseline = j["source"] in baseline_sources
            opened_at = j.get("posted_at") if posted and posted <= now else (None if baseline else now_s)
            state[k] = {"first_seen": now_s, "last_seen": now_s, "closed_at": None, "reposts": 0,
                        "opened_at": opened_at, "baseline": baseline, "source": j["source"],
                        "company": j["company_slug"], "title": j["title"], "family": j["family"]}
            if not baseline:
                opened.append(k)
        elif s.get("closed_at"):
            closed_at = parse_ts(s["closed_at"])
            if closed_at and now - closed_at <= timedelta(days=config.REPOST_LOOKBACK_DAYS):
                s["reposts"] = s.get("reposts", 0) + 1
            s.update({"first_seen": now_s, "last_seen": now_s, "closed_at": None, "baseline": False,
                      "opened_at": now_s})
            opened.append(k)
            reopened.append(k)
        else:
            s["last_seen"] = now_s
            s["source"] = j["source"]
    closed = []
    for k, s in state.items():
        if k in present or s.get("closed_at"):
            continue
        if s.get("source") in ok_sources:
            s["closed_at"] = now_s
            closed.append(k)
    # forget long-closed entries
    cutoff = now - timedelta(days=config.CLOSED_KEEP_DAYS)
    for k in [k for k, s in state.items() if s.get("closed_at") and parse_ts(s["closed_at"]) < cutoff]:
        del state[k]
    return opened, closed, reopened
