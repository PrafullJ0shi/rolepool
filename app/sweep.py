"""One sweep: fetch every board, normalise, de-duplicate, diff, score, write data, feeds and site copies.

    python -m app.sweep            full sweep
    python -m app.sweep --limit 20 first 20 companies only (for a quick local check)
"""
from __future__ import annotations

import argparse
import shutil
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import yaml

from . import config, scoring
from .dedupe import dedupe_by_key, merge_boards_into_ats
from .detect import crypto_relevance
from .feeds import build_all
from .fx import usd_rates
from .http import Client
from .normalize import build
from .sources import ats as ats_mod
from .sources import boards as boards_mod
from .store import load, save
from .text import slugify
from .tracking import apply_diff, iso, parse_ts

D = config.DATA


def load_companies(limit: int | None = None) -> list[dict]:
    rows = yaml.safe_load((D / "companies.yml").read_text())["companies"]
    rows = [r for r in rows if r.get("status") != "no-board" and r.get("enabled", True)]
    return rows[:limit] if limit else rows


def fetch_ats(client, companies):
    results = {}

    def one(c):
        t0 = time.monotonic()
        try:
            jobs, err = ats_mod.ADAPTERS[c["ats"]](client, c["token"])
        except Exception as e:  # noqa: BLE001
            jobs, err = None, f"error: {type(e).__name__}"
        return c, jobs, err, round(time.monotonic() - t0, 2)

    with ThreadPoolExecutor(config.MAX_WORKERS) as ex:
        for c, jobs, err, secs in ex.map(one, companies):
            results[c["name"]] = (c, jobs, err, secs)
    return results


def fetch_boards(client):
    out = {}
    for name, fn in boards_mod.FETCHERS.items():
        try:
            jobs, err = fn(client)
        except Exception as e:  # noqa: BLE001
            jobs, err = None, f"error: {type(e).__name__}"
        out[name] = (jobs, err)
    return out


def daily_rows(state: dict, hist_series: list[dict], slug: str, today: date, window: int = 30):
    """Per-day opened/closed for one company from state, with prev_open from history (or current)."""
    opened, closed = Counter(), Counter()
    for s in state.values():
        if s["company"] != slug:
            continue
        oa = parse_ts(s.get("opened_at"))
        if oa:
            opened[oa.date()] += 1
        ca = parse_ts(s.get("closed_at"))
        if ca:
            closed[ca.date()] += 1
    open_by_day = {date.fromisoformat(r["d"]): r["n"] for r in hist_series}
    rows = []
    for age in range(window):
        d = date.fromordinal(today.toordinal() - age)
        if not opened[d] and not closed[d]:
            continue
        prev = open_by_day.get(d - timedelta(days=1))
        if prev is None:
            prev = open_by_day.get(d, None)
        rows.append({"date": d, "opened": opened[d], "closed": closed[d], "prev_open": prev or 0})
    return rows, opened, closed


def run(limit: int | None = None) -> dict:
    t_start = time.monotonic()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    now_s, today = iso(now), now.date()
    client = Client()
    fx, fx_src = usd_rates(client)

    companies = load_companies(limit)
    state = load(D / "state.json", {})
    history = load(D / "history.json", {"sweeps": [], "companies": {}})
    prev_companies = {c["slug"]: c for c in load(D / "companies.json", {"companies": []})["companies"]}
    known_sources = set(load(D / "meta.json", {}).get("tracked_sources", []))

    ats_res = fetch_ats(client, companies)
    board_res = fetch_boards(client)

    # ---------------------------------------------------------- normalise
    ats_jobs, health, ok_sources = [], [], set()
    for name, (c, jobs, err, secs) in ats_res.items():
        src = f"{c['ats']}:{c['token']}"
        ok = jobs is not None
        health.append({"company": name, "slug": slugify(name), "ats": c["ats"], "token": c["token"],
                       "ok": ok, "jobs": len(jobs or []), "error": err, "seconds": secs})
        if not ok:
            continue
        ok_sources.add(src)
        for raw in jobs:
            if not raw.get("title") or not raw.get("url"):
                continue
            if c.get("filter") == "crypto" and crypto_relevance(
                    f"{raw['title']} {raw.get('department') or ''} {raw.get('description', '')[:4000]}") < config.RELEVANCE_MIN:
                continue
            j = build(raw, company=name, source=src, kind="ats", fx=fx, company_kind=c.get("kind", "company"))
            ats_jobs.append(j)
    ats_jobs, dup_ats = dedupe_by_key(ats_jobs)

    board_jobs, board_health = [], []
    for name, (jobs, err) in board_res.items():
        kept = 0
        if jobs is not None:
            ok_sources.add(f"board:{name}")
            for raw in jobs:
                if not raw.get("title") or not raw.get("url") or not raw.get("company"):
                    continue
                if not boards_mod.is_relevant(name, raw, config.RELEVANCE_MIN):
                    continue
                j = build(raw, company=raw["company"].strip(), source=f"board:{name}", kind="board", fx=fx)
                board_jobs.append(j)
                kept += 1
        board_health.append({"board": name, "label": boards_mod.BOARDS[name]["label"],
                             "home": boards_mod.BOARDS[name]["home"], "ok": jobs is not None,
                             "items": len(jobs or []), "kept": kept, "error": err})
    board_jobs, merged = merge_boards_into_ats(ats_jobs, board_jobs)
    board_jobs, dup_boards = dedupe_by_key(board_jobs)
    jobs = ats_jobs + board_jobs

    # ---------------------------------------------------------- diff
    baseline_sources = {s for s in ok_sources if s not in known_sources}
    opened_keys, closed_keys, reopened_keys = apply_diff(state, jobs, ok_sources, now, baseline_sources)
    opened_set = set(opened_keys)

    # ---------------------------------------------------------- per-company metrics
    by_company = defaultdict(list)
    for j in jobs:
        if j["source_kind"] == "ats":
            by_company[j["company_slug"]].append(j)
    closed_by_company = Counter(state[k]["company"] for k in closed_keys if k in state)
    opened_by_company = Counter(state[k]["company"] for k in opened_keys if k in state)

    comp_rows, momenta = [], {}
    for h in health:
        slug = h["slug"]
        series = history["companies"].setdefault(slug, {"name": h["company"], "series": []})["series"]
        rows, opened_ctr, closed_ctr = daily_rows(state, series, slug, today)
        m = scoring.momentum(rows, today)
        momenta[slug] = m
        h["_rows"], h["_opened"], h["_closed"] = rows, opened_ctr, closed_ctr

    xs = [momenta[h["slug"]] for h in health if h["ok"] and h["jobs"] > 0]
    flips = load(D / "flips.json", [])
    for h in health:
        slug = h["slug"]
        series = history["companies"][slug]["series"]
        own_hist = [r["m"] for r in series if r.get("m") is not None and r["d"] != today.isoformat()]
        sc = scoring.hiring_score(momenta[slug], own_hist[-60:], xs)
        cj = by_company.get(slug, [])
        open_now = len(cj) if h["ok"] else (prev_companies.get(slug, {}).get("open", 0))
        last30 = [r["n"] for r in series if date.fromisoformat(r["d"]) >= today - timedelta(days=30)]
        open_max_30 = max(last30 + [open_now]) if (last30 or open_now) else 0
        o7 = sum(v for d, v in h["_opened"].items() if d > today - timedelta(days=7))
        o30 = sum(v for d, v in h["_opened"].items() if d > today - timedelta(days=30))
        c7 = sum(v for d, v in h["_closed"].items() if d > today - timedelta(days=7))
        c30 = sum(v for d, v in h["_closed"].items() if d > today - timedelta(days=30))
        open_dates = [d for d in h["_opened"]]
        last_new = max(open_dates) if open_dates else None
        no_new = (today - last_new).days if last_new else None

        def open_ago(days):
            target = (today - timedelta(days=days)).isoformat()
            older = [r for r in series if r["d"] <= target]
            return older[-1]["n"] if older else None
        o_7ago, o_30ago = open_ago(7), open_ago(30)
        zero_streak = 0
        for r in reversed(series):
            if r["n"] == 0:
                zero_streak += 1
            else:
                break
        if open_now == 0:
            zero_streak += 1
        st = scoring.company_state(fetched_ok=h["ok"], open_now=open_now, open_max_30d=open_max_30, no_new_days=no_new,
                                   net_30d=o30 - c30, new_7d=o7, H=sc["H"], zero_streak=zero_streak)
        prev_state = prev_companies.get(slug, {}).get("state")
        board_url = ats_mod.BOARD_URL[h["ats"]].format(t=h["token"])
        if prev_state and prev_state != st:
            flips.insert(0, {"company": h["company"], "from": prev_state, "to": st, "at": now_s, "board": board_url,
                             "why": f"H={sc['H']}, open={open_now}, new 7d={o7}, closed 7d={c7}, days since a new role={no_new}"})
        fam = Counter(j["family"] for j in cj)
        sal = [j["salary"]["mid_usd"] for j in cj if j.get("salary")]
        comp_rows.append({
            "name": h["company"], "slug": slug, "ats": h["ats"], "board": board_url, "ok": h["ok"], "error": h["error"],
            "open": open_now, "opened_sweep": opened_by_company.get(slug, 0), "closed_sweep": closed_by_company.get(slug, 0),
            "new_7d": o7, "new_30d": o30, "closed_7d": c7, "closed_30d": c30, "net_7d": o7 - c7, "net_30d": o30 - c30,
            "delta_7d": (open_now - o_7ago) if o_7ago is not None else None,
            "delta_30d": (open_now - o_30ago) if o_30ago is not None else None,
            "days_since_new": no_new, "momentum": round(momenta[slug], 5), **sc, "state": st,
            "families": dict(fam.most_common()), "remote_share": round(sum(j["workplace"] == "remote" for j in cj) / len(cj), 3) if cj else None,
            "median_salary_usd": round(statistics.median(sal), -3) if sal else None,
            "kind": next((c.get("kind", "company") for c in companies if c["name"] == h["company"]), "company"),
        })
        row = {"d": today.isoformat(), "n": open_now, "o": opened_by_company.get(slug, 0),
               "c": closed_by_company.get(slug, 0), "m": round(momenta[slug], 5), "H": sc["H"]}
        if series and series[-1]["d"] == row["d"]:
            row["o"] += series[-1]["o"]
            row["c"] += series[-1]["c"]
            series[-1] = row
        else:
            series.append(row)
        del series[:-400]
    state_of = {c["slug"]: c["state"] for c in comp_rows}

    # ---------------------------------------------------------- per-job scores and output rows
    out_jobs = []
    for j in jobs:
        s = state[j["key"]]
        opened_at = s.get("opened_at")
        ref = parse_ts(opened_at) or parse_ts(s["first_seen"])
        age = max(0.0, (now - ref).total_seconds() / 86400)
        g = scoring.ghost_score(age_days=age, reposts=s.get("reposts", 0), title=j["title"], desc_len=j.get("desc_len"),
                                company_state_=state_of.get(j["company_slug"], "STEADY"))
        is_new = bool(opened_at) and (now - parse_ts(opened_at)) <= timedelta(days=config.NEW_WINDOW_DAYS)
        out_jobs.append({**{k: v for k, v in j.items() if k not in ("desc_len",)},
                         "first_seen": s["first_seen"], "opened_at": opened_at, "baseline": s.get("baseline", False),
                         "age_days": round(age, 1), "age_known": bool(opened_at), "fresh": scoring.freshness(age),
                         "ghost": g["G"], "ghost_parts": g["parts"], "reposts": s.get("reposts", 0),
                         "new": is_new, "new_this_sweep": j["key"] in opened_set})
    out_jobs.sort(key=lambda x: (x["opened_at"] or "", x["first_seen"]), reverse=True)

    # ---------------------------------------------------------- sector history
    fam_counts = Counter(j["family"] for j in out_jobs)
    reg_counts = Counter(r for j in out_jobs for r in j["regions"])
    sweep_row = {"d": today.isoformat(), "at": now_s, "open": len(out_jobs),
                 "open_ats": len(ats_jobs), "open_boards": len(board_jobs),
                 "opened": len(opened_keys), "closed": len(closed_keys), "reopened": len(reopened_keys),
                 "companies_ok": sum(h["ok"] for h in health), "companies_failed": sum(not h["ok"] for h in health),
                 "by_family": dict(fam_counts.most_common()), "by_region": dict(reg_counts.most_common()),
                 "states": dict(Counter(state_of.values()))}
    if history["sweeps"] and history["sweeps"][-1]["d"] == sweep_row["d"]:
        last = history["sweeps"][-1]
        sweep_row["opened"] += last["opened"]
        sweep_row["closed"] += last["closed"]
        history["sweeps"][-1] = sweep_row
    else:
        history["sweeps"].append(sweep_row)

    src_counts = Counter(j["source"].split(":")[0] if j["source_kind"] == "ats" else j["source"] for j in out_jobs)
    meta = {
        "brand": config.BRAND, "swept_at": now_s, "duration_s": round(time.monotonic() - t_start, 1),
        "fx": fx_src, "jobs": len(out_jobs), "jobs_ats": len(ats_jobs), "jobs_boards": len(board_jobs),
        "companies": len(health), "companies_ok": sweep_row["companies_ok"], "companies_failed": sweep_row["companies_failed"],
        "companies_with_jobs": sum(1 for c in comp_rows if c["open"] > 0),
        "employers_total": len({j["company_slug"] for j in out_jobs}),
        "opened": len(opened_keys), "closed": len(closed_keys), "reopened": len(reopened_keys),
        "dedupe": {"ats_exact": dup_ats, "board_into_ats": merged, "board_exact": dup_boards},
        "by_source": dict(src_counts.most_common()),
        "with_salary": sum(1 for j in out_jobs if j.get("salary")),
        "with_posted_date": sum(1 for j in out_jobs if j.get("posted_at")),
        "boards": board_health, "http": client.stats, "first_sweep": not known_sources,
        "tracked_sources": sorted(known_sources | ok_sources),
    }
    flips = flips[:500]

    # ---------------------------------------------------------- write
    save(D / "state.json", state, compact=True)
    save(D / "history.json", history, compact=True)
    save(D / "companies.json", {"swept_at": now_s, "companies": sorted(comp_rows, key=lambda c: -c["open"])})
    save(D / "jobs.json", {"swept_at": now_s, "jobs": out_jobs}, compact=True)
    save(D / "health.json", {"swept_at": now_s, "ats": sorted(health_clean(health), key=lambda h: (h["ok"], h["company"].lower())),
                             "boards": board_health})
    save(D / "flips.json", flips)
    save(D / "meta.json", meta)
    publish(out_jobs, comp_rows, history, meta, flips, now_s)
    client.close()
    return meta


def health_clean(health):
    return [{k: v for k, v in h.items() if not k.startswith("_")} for h in health]


def site_job(j: dict) -> list:
    """Compact row for the browser. Column order documented in site/js/app.js (COLS)."""
    sal = j.get("salary")
    return [j["key"], j["company"], j["title"], j["url"], j["source"], j["location"], j["countries"], j["regions"],
            j["workplace"], j["seniority"], j["family"],
            [sal["min_usd"], sal["max_usd"], sal["label"]] if sal else None,
            (j.get("posted_at") or "")[:10], j["first_seen"][:10], (j.get("opened_at") or "")[:10],
            j["fresh"], j["ghost"], 1 if j["new"] else 0, 1 if j["new_this_sweep"] else 0, j["also_on"],
            j["company_slug"], j["source_kind"], j.get("reposts", 0)]


def publish(jobs, comps, history, meta, flips, now_s):
    sd = config.SITE / "data"
    sd.mkdir(parents=True, exist_ok=True)
    save(sd / "jobs.json", {"swept_at": now_s, "rows": [site_job(j) for j in jobs]}, compact=True)
    save(sd / "companies.json", {"swept_at": now_s, "companies": comps}, compact=True)
    trimmed = {"sweeps": history["sweeps"][-400:],
               "companies": {k: {"name": v["name"], "series": [[r["d"], r["n"], r["o"], r["c"], r.get("H")] for r in v["series"][-120:]]}
                             for k, v in history["companies"].items()}}
    save(sd / "history.json", trimmed, compact=True)
    save(sd / "meta.json", meta)
    save(sd / "flips.json", flips[:100], compact=True)
    shutil.copy(D / "health.json", sd / "health.json")
    for path, xml in build_all(jobs, flips, now_s).items():
        p = config.SITE / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(xml)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    meta = run(args.limit)
    print({k: v for k, v in meta.items() if k not in ("boards", "tracked_sources")})


if __name__ == "__main__":
    main()
