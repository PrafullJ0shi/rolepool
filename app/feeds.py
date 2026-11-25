"""Atom feeds: all new roles, one per role family, region, remote, and company state flips."""
from __future__ import annotations

from xml.sax.saxutils import escape

from . import config
from .text import slugify


def _entry(j: dict) -> str:
    sal = f" · {j['salary']['label']}" if j.get("salary") else ""
    summary = (f"{j['company']} · {j['family']} · {j['seniority']} · {j['workplace']} · "
               f"{j['location'] or 'location not stated'}{sal}. Source: {j['source']}. "
               f"First seen by the sweep {j['first_seen'][:10]}.")
    return (
        "<entry>"
        f"<title>{escape(j['title'])} — {escape(j['company'])}</title>"
        f"<link href=\"{escape(j['url'])}\"/>"
        f"<id>urn:rolepool:{j['key']}</id>"
        f"<updated>{j.get('opened_at') or j['first_seen']}</updated>"
        f"<published>{j.get('posted_at') or j['first_seen']}</published>"
        f"<category term=\"{escape(j['family'])}\"/>"
        f"<summary>{escape(summary)}</summary>"
        "</entry>"
    )


def atom(title: str, path: str, jobs: list[dict], updated: str) -> str:
    entries = "".join(_entry(j) for j in jobs)
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        f"<title>{escape(config.BRAND)}: {escape(title)}</title>"
        f"<link href=\"{config.SITE_URL}\"/>"
        f"<link rel=\"self\" href=\"{config.SITE_URL}{path}\"/>"
        f"<id>{config.SITE_URL}{path}</id>"
        f"<updated>{updated}</updated>"
        f"<author><name>{escape(config.BRAND)}</name></author>"
        f"{entries}</feed>\n"
    )


def flips_atom(flips: list[dict], updated: str) -> str:
    entries = []
    for f in flips[:200]:
        entries.append(
            "<entry>"
            f"<title>{escape(f['company'])}: {f['from']} → {f['to']}</title>"
            f"<link href=\"{escape(f.get('board') or config.SITE_URL)}\"/>"
            f"<id>urn:rolepool:flip:{slugify(f['company'])}:{f['at']}</id>"
            f"<updated>{f['at']}</updated>"
            f"<summary>{escape(f['why'])}</summary>"
            "</entry>")
    return (
        '<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom">'
        f"<title>{escape(config.BRAND)}: company state changes</title>"
        f"<link href=\"{config.SITE_URL}\"/><link rel=\"self\" href=\"{config.SITE_URL}feed/flips.xml\"/>"
        f"<id>{config.SITE_URL}feed/flips.xml</id><updated>{updated}</updated>"
        f"<author><name>{escape(config.BRAND)}</name></author>{''.join(entries)}</feed>\n")


def build_all(jobs: list[dict], flips: list[dict], updated: str, limit: int = 200) -> dict[str, str]:
    """Return {relative path: xml}. Jobs are sorted newest first by first_seen then posted date."""
    def order(j):
        return (j.get("opened_at") or "", j["first_seen"])
    fresh = sorted((j for j in jobs if j.get("opened_at")), key=order, reverse=True)
    out = {"feed/all.xml": atom("all new roles", "feed/all.xml", fresh[:limit], updated)}
    fams = sorted({j["family"] for j in jobs})
    for f in fams:
        p = f"feed/family/{slugify(f)}.xml"
        out[p] = atom(f"{f} roles", p, [j for j in fresh if j["family"] == f][:limit], updated)
    for r in ["North America", "Latin America", "Europe", "Middle East & Africa", "Asia-Pacific", "Global"]:
        p = f"feed/region/{slugify(r)}.xml"
        out[p] = atom(f"roles in {r}", p, [j for j in fresh if r in j["regions"]][:limit], updated)
    out["feed/remote.xml"] = atom("remote roles", "feed/remote.xml", [j for j in fresh if j["workplace"] == "remote"][:limit], updated)
    out["feed/salary.xml"] = atom("roles with a published salary", "feed/salary.xml", [j for j in fresh if j.get("salary")][:limit], updated)
    out["feed/flips.xml"] = flips_atom(flips, updated)
    return out
