"""Opt-in GitHub alerts: one open issue per role family, one digest comment per sweep.

Readers subscribe to the issue they care about; GitHub delivers the notification. The workflow runs
this with its built-in GITHUB_TOKEN (permissions: issues: write), so no secret is configured.

    python -m app.alerts --dry-run     print the digests
    python -m app.alerts               post them (needs GITHUB_TOKEN and GITHUB_REPOSITORY)
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections import defaultdict

from . import config
from .detect import FAMILIES
from .store import load

API = "https://api.github.com"
MAX_PER_COMMENT = 60


def digests(jobs: list[dict]) -> dict[str, str]:
    by_family = defaultdict(list)
    for j in jobs:
        if j.get("new_this_sweep"):
            by_family[j["family"]].append(j)
    out = {}
    for fam, rows in by_family.items():
        rows.sort(key=lambda j: (j["company"].lower(), j["title"].lower()))
        lines = [f"**{len(rows)} new {fam} role{'s' if len(rows) != 1 else ''}** in the sweep of {rows[0]['first_seen'][:10]} (UTC).", ""]
        for j in rows[:MAX_PER_COMMENT]:
            sal = f" · {j['salary']['label']}" if j.get("salary") else ""
            where = j["location"] or j["workplace"]
            lines.append(f"- [{j['title']}]({j['url']}) · {j['company']} · {j['seniority']} · {where}{sal}")
        if len(rows) > MAX_PER_COMMENT:
            lines.append(f"- … and {len(rows) - MAX_PER_COMMENT} more on the [board]({config.SITE_URL}#board).")
        lines += ["", f"Feed: {config.SITE_URL}feed/family/{fam.lower().replace(' & ', '-').replace(' ', '-')}.xml"]
        out[fam] = "\n".join(lines)
    return out


def _req(method: str, path: str, token: str, body: dict | None = None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "User-Agent": config.USER_AGENT, "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def post(texts: dict[str, str], repo: str, token: str) -> None:
    issues = _req("GET", f"/repos/{repo}/issues?labels=alerts&state=open&per_page=100", token) or []
    by_title = {i["title"]: i["number"] for i in issues}
    for fam in FAMILIES:
        if fam not in texts:
            continue
        title = f"Alerts: {fam}"
        num = by_title.get(title)
        if num is None:
            created = _req("POST", f"/repos/{repo}/issues", token, {
                "title": title, "labels": ["alerts"],
                "body": (f"Subscribe to this issue to get a notification after each daily sweep that finds new {fam} roles. "
                         f"Unsubscribe at any time. Board: {config.SITE_URL}")})
            num = created["number"]
        _req("POST", f"/repos/{repo}/issues/{num}/comments", token, {"body": texts[fam]})
        print(f"posted {fam} to #{num}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    jobs = load(config.DATA / "jobs.json", {"jobs": []})["jobs"]
    texts = digests(jobs)
    if args.dry_run or not os.environ.get("GITHUB_TOKEN"):
        for fam, t in texts.items():
            print(f"--- {fam}\n{t}\n")
        print(f"{len(texts)} digests (dry run)")
        return
    post(texts, os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"])


if __name__ == "__main__":
    main()
