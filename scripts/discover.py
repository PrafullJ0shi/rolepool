"""One-off board discovery. Builds data/companies.yml.

1. Seeds crypto companies from the original crawler's public company list (names and
   board tokens only; tokens are facts, no code is reused).
2. Probes every extra candidate name on each public ATS API.
3. Keeps boards that answer, and for new candidates only those whose postings read as
   crypto (keyword check), so a shared slug such as "ultra" does not pull in a stranger.

Run:  python -m scripts.discover  (takes a few minutes, polite rate limits)
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config  # noqa: E402
from app.http import Client  # noqa: E402
from app.sources.ats import ADAPTERS  # noqa: E402
from app.detect import crypto_relevance  # noqa: E402

SEED_URL = "https://raw.githubusercontent.com/crypto-jobs-fyi/crawler/main/companies.json"
SCRAPER_MAP = {"GREENHOUSE": "greenhouse", "LEVER": "lever", "ASHBYHQ": "ashby", "WORKABLE": "workable",
               "SMARTRECRUITERS": "smartrecruiters", "RECRUITEE": "recruitee"}


def token_from_url(ats: str, url: str):
    u = url.split("#")[0].rstrip("/")
    if ats == "greenhouse":
        m = re.search(r"greenhouse\.io/(?:embed/job_board\?for=)?([^/?#]+)", u)
    elif ats == "lever":
        m = re.search(r"lever\.co/([^/?#]+)", u)
        if m and ".eu." in u:
            return "lever-eu", m.group(1)
    elif ats == "ashby":
        m = re.search(r"ashbyhq\.com/([^/?#]+)", u)
    elif ats == "workable":
        m = re.search(r"workable\.com/([^/?#]+)", u)
    elif ats == "smartrecruiters":
        m = re.search(r"smartrecruiters\.com/([^/?#]+)", u)
    elif ats == "recruitee":
        m = re.search(r"https?://([^.]+)\.recruitee\.com", u)
    else:
        m = None
    return (ats, m.group(1).replace("%20", " ")) if m else None


def seed_rows(client):
    """Board tokens from the original project's public company list (facts only, no code)."""
    rows = []
    data = client.get_json(SEED_URL)
    for c in (data or {}).get("companies", []):
        if c.get("category") != "crypto" or c.get("scraper") not in SCRAPER_MAP:
            continue
        t = token_from_url(SCRAPER_MAP[c["scraper"]], c["jobs_url"])
        if t:
            rows.append({"name": c["name"], "ats": t[0], "token": t[1], "site": c.get("company_url"), "origin": "seed"})
    return rows


def candidate_rows():
    out = []
    files = [sys.argv[1]] if len(sys.argv) > 1 else ["candidates.txt", "candidates2.txt"]
    lines = []
    for f in files:
        lines += (Path(__file__).parent / f).read_text().splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        name = parts[0]
        slugs = [s for s in (parts[1].split(",") if len(parts) > 1 and parts[1] else []) if s]
        if not slugs:
            slugs = [re.sub(r"[^a-z0-9]", "", name.lower())]
        kind = parts[2] if len(parts) > 2 else "company"
        out.append({"name": name, "slugs": slugs, "kind": kind})
    return out


def probe(client, ats, token):
    try:
        jobs, err = ADAPTERS[ats](client, token)
    except Exception as e:  # noqa: BLE001
        return None, str(e)
    return jobs, err


def main():
    client = Client(rps=3.0, cache=False)
    seeds = seed_rows(client)
    known = {(r["ats"], r["token"].lower()) for r in seeds}
    print(f"seed boards: {len(seeds)}")

    results = []

    def check_seed(r):
        jobs, err = probe(client, r["ats"], r["token"])
        r = dict(r)
        r["jobs"] = len(jobs) if jobs is not None else None
        return r

    with ThreadPoolExecutor(config.MAX_WORKERS) as ex:
        for r in ex.map(check_seed, seeds):
            results.append(r)
            print("seed", r["ats"], r["token"], r["jobs"])

    cands = candidate_rows()
    tasks = []
    for c in cands:
        for s in c["slugs"]:
            for ats in ("greenhouse", "lever", "ashby", "workable", "smartrecruiters", "recruitee"):
                if (ats, s.lower()) in known:
                    continue
                tasks.append((c, ats, s))
    print(f"candidate probes: {len(tasks)}")

    def check_cand(t):
        c, ats, s = t
        jobs, err = probe(client, ats, s)
        if not jobs:
            return None
        rel = sum(crypto_relevance(j["title"] + " " + (j.get("department") or "") + " " + j.get("description", "")[:3000]) for j in jobs)
        hit_share = sum(1 for j in jobs if crypto_relevance(j["title"] + " " + j.get("description", "")[:3000]) >= 2) / len(jobs)
        return {"name": c["name"], "ats": ats, "token": s, "jobs": len(jobs), "kind": c["kind"],
                "relevance": rel, "share": round(hit_share, 2), "origin": "probe"}

    found = []
    with ThreadPoolExecutor(12) as ex:
        for r in ex.map(check_cand, tasks):
            if r:
                print("hit", r)
                found.append(r)

    # keep the best board per candidate name; require crypto signal
    best = {}
    for r in found:
        if r["share"] < 0.25 and r["kind"] != "recruiter":
            continue
        if r["kind"] == "recruiter" and r["share"] < 0.15:
            continue
        k = r["name"]
        if k not in best or r["jobs"] > best[k]["jobs"]:
            best[k] = r

    rows = []
    seen_names = set()
    for r in results:
        key = r["name"].lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        rows.append({"name": r["name"], "ats": r["ats"], "token": r["token"], "kind": "company",
                     "origin": "seed", **({"site": r["site"]} if r.get("site") else {}),
                     **({"status": "no-board"} if r["jobs"] is None else {})})
    for r in best.values():
        if r["name"].lower() in seen_names:
            continue
        seen_names.add(r["name"].lower())
        rows.append({"name": r["name"], "ats": r["ats"], "token": r["token"], "kind": r["kind"], "origin": "probe"})

    manual = yaml.safe_load((Path(__file__).parent / "manual_boards.yml").read_text())["companies"]
    for r in manual:
        if r["name"].lower() not in seen_names:
            seen_names.add(r["name"].lower())
            rows.append(r)
    rows.sort(key=lambda x: x["name"].lower())
    out = config.DATA / "companies.yml"
    header = ("# Boards swept daily. ats + token map to an official public job-board API.\n"
              "# origin: seed = board token taken from the public company list of crypto-jobs-fyi/crawler;\n"
              "#         probe = found by scripts/discover.py and checked for crypto postings;\n"
              "#         manual = scripts/manual_boards.yml.\n")
    out.write_text(header + yaml.safe_dump({"companies": rows}, sort_keys=False, allow_unicode=True))
    (config.DATA / "discovery.json").write_text(json.dumps({"seed": results, "probe_hits": found}, indent=1))
    print(f"wrote {len(rows)} boards; probe hits kept {len(best)} of {len(found)}; stats {client.stats}")


if __name__ == "__main__":
    main()
