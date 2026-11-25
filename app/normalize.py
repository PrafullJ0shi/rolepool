"""Turn a raw adapter job into the one schema the rest of the pipeline uses."""
from __future__ import annotations

import html

from . import detect
from .dedupe import canonical_url, identity_key
from .text import slugify


def fmt_money(v: float) -> str:
    return f"{v/1000:.0f}k" if v < 1_000_000 else f"{v/1_000_000:.2f}M"


def salary_label(sal: dict) -> str:
    sym = {"USD": "$", "EUR": "€", "GBP": "£"}.get(sal["currency"], sal["currency"] + " ")
    lo, hi = float(sal.get("min") or sal.get("max")), float(sal.get("max") or sal.get("min"))
    rng = fmt_money(lo) if lo == hi else f"{fmt_money(lo)}–{fmt_money(hi)}"
    if sal.get("per") in ("hour", "day", "week", "month"):
        rng = (f"{lo:,.0f}" if lo == hi else f"{lo:,.0f}–{hi:,.0f}")
    return f"{sym}{rng}/{ {'year': 'yr', 'month': 'mo', 'hour': 'hr', 'week': 'wk', 'day': 'day'}[sal.get('per') or 'year'] }"


def build(raw: dict, *, company: str, source: str, kind: str, fx: dict, company_kind: str = "company") -> dict:
    title = html.unescape(html.unescape(raw.get("title") or ""))
    loc = raw.get("location") or ""
    desc = raw.get("description") or ""
    wp = detect.workplace(raw.get("workplace"), loc, title, desc)
    hint = raw.get("country_code") or raw.get("country_hint")
    countries, regions = detect.geography(loc + (" " + title if "(" in title else ""), hint)
    if wp == "remote" and not regions:
        regions = ["Global"]
    sal = raw.get("salary")
    origin = "structured" if sal else None
    if not sal and raw.get("salary_text"):
        sal = detect.parse_salary_text(raw["salary_text"])
        origin = "listed" if sal else None
    if not sal and desc:
        sal = detect.parse_salary_text(desc)
        origin = "description" if sal else None
    usd = detect.to_usd_year(sal, fx) if sal else None
    salary = None
    if usd:
        salary = {**usd, "label": salary_label(sal), "currency": sal["currency"], "origin": origin}
    url = canonical_url(raw.get("url") or "")
    return {
        "key": identity_key(company, title, countries, wp),
        "company": company,
        "company_slug": slugify(company),
        "company_kind": company_kind,
        "title": " ".join(title.split()),
        "url": url,
        "source": source,
        "source_kind": kind,
        "also_on": [],
        "location": " ".join(loc.split())[:160],
        "countries": countries,
        "regions": regions,
        "workplace": wp,
        "seniority": detect.seniority(title, raw.get("seniority_hint")),
        "family": detect.role_family(title, raw.get("department")),
        "department": (raw.get("department") or None),
        "employment": raw.get("employment_type"),
        "salary": salary,
        "posted_at": raw.get("posted_at"),
        "desc_len": len(desc) if kind == "ats" else None,
    }
