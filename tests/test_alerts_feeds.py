import xml.etree.ElementTree as ET

from app.alerts import digests
from app.feeds import build_all


def job(i, fam="Engineering", new=True, opened="2026-11-25T03:00:00Z"):
    return {"key": f"k{i}", "title": f"Engineer {i} & co", "company": "Acme", "url": f"https://x.test/{i}", "family": fam,
            "seniority": "Senior", "workplace": "remote", "location": "Remote", "regions": ["Global"], "salary": None,
            "first_seen": "2026-11-25T03:00:00Z", "opened_at": opened, "posted_at": None, "source": "greenhouse:acme",
            "new_this_sweep": new}


def test_digest_groups_new_roles_by_family():
    d = digests([job(1), job(2), job(3, fam="Marketing"), job(4, new=False)])
    assert set(d) == {"Engineering", "Marketing"}
    assert d["Engineering"].startswith("**2 new Engineering roles**")


def test_feeds_are_valid_atom_and_skip_unknown_open_dates():
    feeds = build_all([job(1), job(2, opened=None), job(3, fam="Marketing")], [], "2026-11-25T03:00:00Z")
    assert "feed/all.xml" in feeds and "feed/family/marketing.xml" in feeds and "feed/region/global.xml" in feeds
    root = ET.fromstring(feeds["feed/all.xml"])
    entries = root.findall("{http://www.w3.org/2005/Atom}entry")
    assert len(entries) == 2  # the job with no known open date is left out
    for xml in feeds.values():
        ET.fromstring(xml)
