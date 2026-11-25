"""Adapters for the public job-board APIs that applicant tracking systems publish.

Each adapter takes a polite Client and a board token and returns (jobs, error).
A job is a plain dict with the raw fields every later stage expects:

    ext_id, title, location, department, url, posted_at, workplace,
    employment_type, salary (dict or None), salary_text, description

Nothing here guesses: fields the ATS did not send stay None.
"""
from __future__ import annotations

from ..text import strip_html, to_iso


def _job(**kw) -> dict:
    base = dict(ext_id=None, title="", location="", department=None, url="", posted_at=None,
                workplace=None, employment_type=None, salary=None, salary_text=None,
                description="", country_code=None)
    base.update(kw)
    base["title"] = (base["title"] or "").strip()
    return base


# ---------------------------------------------------------------- Greenhouse
def greenhouse(client, token: str):
    data = client.get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", {"content": "true"})
    if data is None or "jobs" not in data:
        return None, "no board"
    out = []
    for j in data["jobs"]:
        depts = [d.get("name") for d in (j.get("departments") or []) if d.get("name")]
        desc = strip_html(j.get("content"))
        out.append(_job(
            ext_id=str(j.get("id")),
            title=j.get("title"),
            location=(j.get("location") or {}).get("name") or "",
            department=depts[0] if depts else None,
            url=j.get("absolute_url") or "",
            posted_at=to_iso(j.get("first_published")),
            description=desc,
        ))
    return out, None


# ---------------------------------------------------------------- Lever
def lever(client, token: str, eu: bool = False):
    host = "api.eu.lever.co" if eu else "api.lever.co"
    data = client.get_json(f"https://{host}/v0/postings/{token}", {"mode": "json"})
    if not isinstance(data, list):
        return None, "no board"
    out = []
    for j in data:
        cat = j.get("categories") or {}
        sr = j.get("salaryRange") or None
        salary = None
        if sr and (sr.get("min") or sr.get("max")):
            interval = (sr.get("interval") or "").lower()
            per = "year"
            if "hour" in interval:
                per = "hour"
            elif "month" in interval:
                per = "month"
            elif "week" in interval:
                per = "week"
            elif "day" in interval:
                per = "day"
            salary = {"min": sr.get("min"), "max": sr.get("max"), "currency": sr.get("currency"), "per": per}
        locs = cat.get("allLocations") or ([cat.get("location")] if cat.get("location") else [])
        out.append(_job(
            ext_id=j.get("id"),
            title=j.get("text"),
            location=" / ".join(l for l in locs if l),
            department=cat.get("department") or cat.get("team"),
            url=j.get("hostedUrl") or "",
            posted_at=to_iso(j.get("createdAt")),
            workplace=(j.get("workplaceType") or None),
            employment_type=cat.get("commitment"),
            salary=salary,
            salary_text=j.get("salaryDescriptionPlain"),
            description=(j.get("descriptionPlain") or "")[:6000] + " " + (j.get("additionalPlain") or "")[:1500],
            country_code=j.get("country"),
        ))
    return out, None


# ---------------------------------------------------------------- Ashby
_ASHBY_PER = {"1 YEAR": "year", "1 MONTH": "month", "1 WEEK": "week", "1 DAY": "day", "1 HOUR": "hour"}


def ashby(client, token: str):
    data = client.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}", {"includeCompensation": "true"})
    if data is None or "jobs" not in data:
        return None, "no board"
    out = []
    for j in data["jobs"]:
        if j.get("isListed") is False:
            continue
        salary, summary = None, None
        comp = j.get("compensation") or {}
        summary = comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary")
        for tier in comp.get("compensationTiers") or []:
            for c in tier.get("components") or []:
                if (c.get("compensationType") or "").lower() == "salary" and (c.get("minValue") or c.get("maxValue")):
                    salary = {"min": c.get("minValue"), "max": c.get("maxValue"),
                              "currency": c.get("currencyCode"), "per": _ASHBY_PER.get(c.get("interval"), "year")}
                    break
            if salary:
                break
        locs = [j.get("location") or ""] + [s.get("location", "") for s in (j.get("secondaryLocations") or [])]
        wp = (j.get("workplaceType") or "").lower() or ("remote" if j.get("isRemote") else None)
        country = ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry")
        out.append(_job(
            ext_id=j.get("id"),
            title=j.get("title"),
            location=" / ".join(l for l in locs if l),
            department=j.get("department") or j.get("team"),
            url=j.get("jobUrl") or "",
            posted_at=to_iso(j.get("publishedAt")),
            workplace=wp,
            employment_type=j.get("employmentType"),
            salary=salary,
            salary_text=summary,
            description=(j.get("descriptionPlain") or "")[:7000],
            country_hint=country,
        ))
    return out, None


# ---------------------------------------------------------------- Workable
def workable(client, token: str):
    data = client.get_json(f"https://apply.workable.com/api/v1/widget/accounts/{token}", {"details": "true"})
    if data is None or "jobs" not in data:
        return None, "no board"
    out = []
    for j in data["jobs"]:
        locs = j.get("locations") or []
        loc_parts = []
        for l in locs or [{"city": j.get("city"), "region": j.get("state"), "country": j.get("country")}]:
            loc_parts.append(", ".join(p for p in (l.get("city"), l.get("region"), l.get("country")) if p))
        out.append(_job(
            ext_id=j.get("shortcode"),
            title=j.get("title"),
            location=" / ".join(p for p in loc_parts if p),
            department=j.get("department") or j.get("function"),
            url=j.get("url") or j.get("shortlink") or "",
            posted_at=to_iso(j.get("published_on") or j.get("created_at")),
            workplace="remote" if j.get("telecommuting") else None,
            employment_type=j.get("employment_type"),
            description=strip_html(j.get("description")),
            country_code=(locs[0].get("countryCode") if locs else None),
        ))
    return out, None


# ---------------------------------------------------------------- SmartRecruiters
def smartrecruiters(client, token: str):
    out, offset = [], 0
    while True:
        data = client.get_json(f"https://api.smartrecruiters.com/v1/companies/{token}/postings",
                               {"limit": 100, "offset": offset})
        if data is None or "content" not in data:
            return (None, "no board") if offset == 0 else (out, None)
        for j in data["content"]:
            loc = j.get("location") or {}
            wp = "remote" if loc.get("remote") else ("hybrid" if loc.get("hybrid") else None)
            out.append(_job(
                ext_id=j.get("id"),
                title=j.get("name"),
                location=", ".join(p for p in (loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()) if p),
                department=(j.get("department") or {}).get("label") or (j.get("function") or {}).get("label"),
                url=f"https://jobs.smartrecruiters.com/{token}/{j.get('id')}",
                posted_at=to_iso(j.get("releasedDate")),
                workplace=wp,
                employment_type=(j.get("typeOfEmployment") or {}).get("label"),
                country_code=(loc.get("country") or "").upper() or None,
                seniority_hint=(j.get("experienceLevel") or {}).get("label"),
            ))
        offset += 100
        if offset >= data.get("totalFound", 0) or offset >= 1000:
            break
    return out, None


# ---------------------------------------------------------------- Recruitee
def recruitee(client, token: str):
    data = client.get_json(f"https://{token}.recruitee.com/api/offers/")
    if data is None or "offers" not in data:
        return None, "no board"
    out = []
    for j in data["offers"]:
        s = j.get("salary") or {}
        salary = None
        if s.get("min") or s.get("max"):
            per = {"year": "year", "month": "month", "hour": "hour", "week": "week", "day": "day"}.get(
                (s.get("period") or "year").lower(), "year")
            salary = {"min": s.get("min"), "max": s.get("max"), "currency": s.get("currency"), "per": per}
        wp = "remote" if j.get("remote") else ("hybrid" if j.get("hybrid") else ("onsite" if j.get("on_site") else None))
        locs = [l.get("name") or ", ".join(p for p in (l.get("city"), l.get("country")) if p) for l in (j.get("locations") or [])]
        out.append(_job(
            ext_id=str(j.get("id")),
            title=j.get("title"),
            location=" / ".join(l for l in locs if l) or j.get("location") or "",
            department=j.get("department"),
            url=j.get("careers_url") or "",
            posted_at=to_iso(j.get("published_at") or j.get("created_at")),
            workplace=wp,
            employment_type=j.get("employment_type_code"),
            salary=salary,
            description=strip_html(j.get("description")),
            country_code=j.get("country_code"),
        ))
    return out, None


ADAPTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "lever-eu": lambda c, t: lever(c, t, eu=True),
    "ashby": ashby,
    "workable": workable,
    "smartrecruiters": smartrecruiters,
    "recruitee": recruitee,
}

BOARD_URL = {
    "greenhouse": "https://job-boards.greenhouse.io/{t}",
    "lever": "https://jobs.lever.co/{t}",
    "lever-eu": "https://jobs.eu.lever.co/{t}",
    "ashby": "https://jobs.ashbyhq.com/{t}",
    "workable": "https://apply.workable.com/{t}",
    "smartrecruiters": "https://careers.smartrecruiters.com/{t}",
    "recruitee": "https://{t}.recruitee.com",
}
