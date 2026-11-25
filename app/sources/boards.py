"""Crypto job boards and remote boards that publish an official RSS feed or public API.

Checked on 25 Nov 2026 against each site's robots.txt and published API terms:

| Source               | Endpoint                                   | Terms we follow                                     |
| cryptocurrencyjobs   | https://cryptocurrencyjobs.co/index.xml    | Public RSS; robots allows it; link back to listing  |
| cryptojobslist       | https://api.cryptojobslist.com/jobs.rss    | Public RSS advertised from /rss; link back          |
| remoteok             | https://remoteok.com/api?tags=...          | API terms: link back and name Remote OK as source   |
| remotive             | https://remotive.com/api/remote-jobs       | Max 4 calls/day, link back, name Remotive; 24h delay |
| himalayas            | https://himalayas.app/jobs/api/search      | Public API; link back; few pages per query          |

Every board item keeps the board's own URL as the apply link, so traffic goes back to the source.
Items from general remote boards must pass the crypto relevance check (config.RELEVANCE_MIN).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from ..detect import crypto_relevance
from ..text import strip_html, to_iso

BOARDS = {
    "cryptocurrencyjobs": {"label": "Cryptocurrency Jobs", "home": "https://cryptocurrencyjobs.co/", "crypto_native": True},
    "cryptojobslist": {"label": "CryptoJobsList", "home": "https://cryptojobslist.com/", "crypto_native": True},
    "remoteok": {"label": "Remote OK", "home": "https://remoteok.com/", "crypto_native": False},
    "remotive": {"label": "Remotive", "home": "https://remotive.com/", "crypto_native": False},
    "himalayas": {"label": "Himalayas", "home": "https://himalayas.app/", "crypto_native": False},
}

_NS = {"dc": "http://purl.org/dc/elements/1.1/", "media": "http://search.yahoo.com/mrss/"}


def _job(**kw):
    base = dict(ext_id=None, title="", company="", location="", department=None, url="", posted_at=None,
                workplace=None, employment_type=None, salary=None, salary_text=None, description="")
    base.update(kw)
    return base


def _rss_items(client, url):
    r = client.get(url)
    if r is None or r.status_code != 200:
        return None
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return None
    return root.findall("./channel/item")


def cryptocurrencyjobs(client):
    items = _rss_items(client, "https://cryptocurrencyjobs.co/index.xml")
    if items is None:
        return None, "feed unavailable"
    out = []
    for it in items:
        raw = (it.findtext("title") or "").strip()
        m = re.match(r"(.+) at (.+)$", raw)
        title, company = (m.group(1), m.group(2)) if m else (raw, "")
        desc = strip_html(it.findtext("description"))
        link = (it.findtext("link") or "").strip()
        cat = link.split("cryptocurrencyjobs.co/")[-1].split("/")[0] if link else None
        loc = ""
        lm = re.search(r"(?:based in|located in|can be based in) ([^.]+)\.", desc)
        if lm:
            loc = lm.group(1)
        if re.search(r"100% remote|remote", desc, re.I):
            loc = (loc + " / Remote").strip(" /")
        if re.search(r"no geographical restrictions|from anywhere", desc, re.I):
            loc = "Remote, Anywhere"
        out.append(_job(ext_id=link, title=title, company=company, location=loc, department=cat, url=link,
                        posted_at=to_iso(it.findtext("pubDate")), description=desc))
    return out, None


def cryptojobslist(client):
    items = _rss_items(client, "https://api.cryptojobslist.com/jobs.rss")
    if items is None:
        return None, "feed unavailable"
    out = []
    for it in items:
        link = (it.findtext("media:canonical", namespaces=_NS) or it.findtext("link") or "").strip()
        desc = strip_html(it.findtext("description"))
        tags = re.findall(r"Web3 ([A-Z][\w &]+?) Jobs", desc)
        out.append(_job(ext_id=link, title=(it.findtext("title") or "").strip(),
                        company=(it.findtext("dc:creator", namespaces=_NS) or "").strip(),
                        location=(it.findtext("media:location", namespaces=_NS) or "").strip(),
                        department=tags[0] if tags else None, url=link,
                        posted_at=to_iso(it.findtext("pubDate")), description=desc))
    return out, None


def remoteok(client):
    out, seen = [], set()
    for tag in ("crypto", "web3", "blockchain"):
        data = client.get_json("https://remoteok.com/api", {"tags": tag})
        if not isinstance(data, list):
            continue
        for j in data[1:]:
            if not isinstance(j, dict) or j.get("id") in seen:
                continue
            seen.add(j.get("id"))
            sal = None
            if j.get("salary_min") and j.get("salary_max"):
                sal = {"min": j["salary_min"], "max": j["salary_max"], "currency": "USD", "per": "year"}
            out.append(_job(ext_id=str(j.get("id")), title=j.get("position") or "", company=j.get("company") or "",
                            location=("Remote" + (", " + j["location"] if j.get("location") else "")),
                            department=", ".join((j.get("tags") or [])[:3]), url=j.get("url") or "",
                            posted_at=to_iso(j.get("date")), workplace="remote", salary=sal,
                            description=strip_html(j.get("description")) + " " + " ".join(j.get("tags") or [])))
    return (out, None) if out else (None, "api unavailable")


def remotive(client):
    out, seen = [], set()
    for q in ("crypto", "blockchain", "web3"):
        data = client.get_json("https://remotive.com/api/remote-jobs", {"search": q})
        if not data or "jobs" not in data:
            continue
        for j in data["jobs"]:
            if j.get("id") in seen:
                continue
            seen.add(j.get("id"))
            out.append(_job(ext_id=str(j.get("id")), title=j.get("title") or "", company=j.get("company_name") or "",
                            location="Remote, " + (j.get("candidate_required_location") or "Anywhere"),
                            department=j.get("category"), url=j.get("url") or "",
                            posted_at=to_iso(j.get("publication_date")), workplace="remote",
                            employment_type=j.get("job_type"), salary_text=j.get("salary") or None,
                            description=strip_html(j.get("description")) + " " + " ".join(j.get("tags") or [])))
    return (out, None) if out else (None, "api unavailable")


def himalayas(client, pages: int = 6):
    out, seen = [], set()
    for q in ("crypto", "web3", "blockchain"):
        for page in range(1, pages + 1):
            data = client.get_json("https://himalayas.app/jobs/api/search", {"q": q, "page": page})
            if not data or not data.get("jobs"):
                break
            for j in data["jobs"]:
                g = j.get("guid")
                if g in seen:
                    continue
                seen.add(g)
                sal = None
                if j.get("minSalary") and j.get("currency"):
                    per = {"annual": "year", "monthly": "month", "hourly": "hour", "weekly": "week", "daily": "day"}.get(
                        j.get("salaryPeriod") or "annual", "year")
                    sal = {"min": j["minSalary"], "max": j.get("maxSalary") or j["minSalary"], "currency": j["currency"], "per": per}
                locs = j.get("locationRestrictions") or []
                out.append(_job(ext_id=g, title=j.get("title") or "", company=j.get("companyName") or "",
                                location="Remote" + (", " + ", ".join(locs) if locs else ", Anywhere"),
                                department=", ".join(j.get("parentCategories") or []), url=g or "",
                                posted_at=to_iso(j.get("pubDate")), workplace="remote", salary=sal,
                                employment_type=j.get("employmentType"),
                                description=strip_html(j.get("description")) + " " + " ".join(j.get("categories") or []),
                                seniority_hint=(j.get("seniority") or [None])[0]))
            if page * 20 >= data.get("totalCount", 0):
                break
    return (out, None) if out else (None, "api unavailable")


FETCHERS = {
    "cryptocurrencyjobs": cryptocurrencyjobs,
    "cryptojobslist": cryptojobslist,
    "remoteok": remoteok,
    "remotive": remotive,
    "himalayas": himalayas,
}


def is_relevant(source: str, job: dict, min_points: float) -> bool:
    if BOARDS[source]["crypto_native"]:
        return True
    text = f"{job['title']} {job.get('department') or ''} {job.get('description', '')[:4000]}"
    return crypto_relevance(text) >= min_points
