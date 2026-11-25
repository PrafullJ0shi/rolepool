from datetime import datetime, timedelta, timezone

from app.tracking import apply_diff

T0 = datetime(2026, 11, 25, 3, 0, tzinfo=timezone.utc)


def job(key, source="greenhouse:acme", posted=None):
    return {"key": key, "source": source, "company_slug": "acme", "title": key, "family": "Engineering", "posted_at": posted}


def test_first_sweep_is_baseline_without_opens():
    st = {}
    opened, closed, _ = apply_diff(st, [job("a"), job("b", posted="2026-11-20T00:00:00Z")], {"greenhouse:acme"}, T0, {"greenhouse:acme"})
    assert opened == [] and closed == []
    assert st["a"]["opened_at"] is None and st["a"]["baseline"]
    assert st["b"]["opened_at"] == "2026-11-20T00:00:00Z"


def test_open_close_and_repost():
    st = {}
    src = {"greenhouse:acme"}
    apply_diff(st, [job("a"), job("b")], src, T0, src)
    t1 = T0 + timedelta(days=1)
    opened, closed, _ = apply_diff(st, [job("a"), job("c")], src, t1, set())
    assert opened == ["c"] and closed == ["b"]
    assert st["c"]["opened_at"] == "2026-11-26T03:00:00Z"
    t2 = T0 + timedelta(days=5)
    opened, closed, reopened = apply_diff(st, [job("a"), job("b"), job("c")], src, t2, set())
    assert reopened == ["b"] and st["b"]["reposts"] == 1 and st["b"]["closed_at"] is None


def test_failed_source_never_closes():
    st = {}
    apply_diff(st, [job("a")], {"greenhouse:acme"}, T0, {"greenhouse:acme"})
    opened, closed, _ = apply_diff(st, [], set(), T0 + timedelta(days=1), set())
    assert closed == [] and st["a"]["closed_at"] is None


def test_old_closed_entries_are_forgotten():
    st = {}
    src = {"greenhouse:acme"}
    apply_diff(st, [job("a")], src, T0, src)
    apply_diff(st, [], src, T0 + timedelta(days=1), set())
    apply_diff(st, [], src, T0 + timedelta(days=200), set())
    assert "a" not in st
