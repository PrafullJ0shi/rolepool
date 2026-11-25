"""Canonical URLs, job identity keys and cross-source de-duplication.

Identity key (one per opening):
    key = sha1( norm_company(company) | norm_title(title) | loc_bucket(countries, workplace) )[:16]

Cross-source match (board item vs a company's own ATS posting):
    same hard-normalised company AND ( norm_title equal OR token Jaccard >= JACCARD_MIN )
The ATS copy wins; the board is kept in `also_on`.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

JACCARD_MIN = 0.85
_DROP_PARAMS = re.compile(r"^(utm_.*|gh_src|ref|source|src|lever-source.*|lever-origin|fbclid|gclid|mc_.*|trk|_hs.*|campaign)$", re.I)
_LEGAL = r"\b(inc|incorporated|llc|ltd|limited|gmbh|ag|sa|s\.a\.|bv|b\.v\.|plc|pte|corp|corporation|co|company|oy|ab|srl|sas)\b\.?"
_TLD = r"\.(com|io|xyz|org|net|fi|co|finance|network|app|global|ai|me|cash|trade|exchange|money|dev)\b"
_SOFT = r"\b(labs?|foundation|network|protocol|technologies|technology|group|hq|official|careers|crypto|digital|global|holdings)\b"
_ABBR = [(r"\bsr\b\.?", "senior"), (r"\bjr\b\.?", "junior"), (r"\beng\b", "engineer"), (r"\bmgr\b", "manager"),
         (r"\bdev\b", "developer"), (r"\bswe\b", "software engineer"), (r"&", " and "), (r"\bvp\b", "vice president"),
         (r"\bbiz ?dev\b", "business development"), (r"\bbd\b", "business development")]
_NOISE = r"\b(remote|hybrid|on-?site|onsite|full[- ]?time|part[- ]?time|contract|contractor|permanent|temporary|wfh|anywhere|worldwide|global|m/f/d|f/m/d|w/m/d|all genders|req\w*\s?#?\d+)\b"


def canonical_url(url: str) -> str:
    if not url:
        return ""
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=False) if not _DROP_PARAMS.match(k) and v not in ("NaN", "null")]
    path = re.sub(r"/+$", "", p.path) or "/"
    return urlunsplit(("https", p.netloc.lower(), path, urlencode(q), ""))


def norm_company(name: str, hard: bool = False) -> str:
    s = (name or "").lower()
    s = re.sub(_TLD, " ", s)
    s = re.sub(_LEGAL, " ", s)
    if hard:
        s = re.sub(_SOFT, " ", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s or re.sub(r"[^a-z0-9]+", "", (name or "").lower())


def norm_title(title: str) -> str:
    s = (title or "").lower()
    s = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", s)
    for rx, rep in _ABBR:
        s = re.sub(rx, rep, s)
    s = re.sub(_NOISE, " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def loc_bucket(countries: list[str], workplace: str) -> str:
    if countries:
        return "+".join(sorted(countries)[:3])
    return "remote" if workplace == "remote" else "any"


def identity_key(company: str, title: str, countries: list[str], workplace: str) -> str:
    raw = f"{norm_company(company)}|{norm_title(title)}|{loc_bucket(countries, workplace)}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def jaccard(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def merge_boards_into_ats(ats_jobs: list[dict], board_jobs: list[dict]) -> tuple[list[dict], int]:
    """Drop board items that duplicate an ATS posting (recording the board in also_on) or each other.

    Returns (kept board jobs, number merged)."""
    index: dict[str, list[dict]] = {}
    for j in ats_jobs:
        index.setdefault(norm_company(j["company"], hard=True), []).append(j)
    kept: dict[str, dict] = {}
    merged = 0
    for b in board_jobs:
        ck = norm_company(b["company"], hard=True)
        nt = norm_title(b["title"])
        hit = None
        for j in index.get(ck, []):
            jt = j.setdefault("_nt", norm_title(j["title"]))
            if jt == nt or jaccard(jt, nt) >= JACCARD_MIN:
                hit = j
                break
        if hit is not None:
            if b["source"] not in hit["also_on"]:
                hit["also_on"].append(b["source"])
            merged += 1
            continue
        bk = f"{ck}|{nt}"
        if bk in kept:
            other = kept[bk]
            if b["source"] not in other["also_on"] and b["source"] != other["source"]:
                other["also_on"].append(b["source"])
            if b.get("posted_at") and (not other.get("posted_at") or b["posted_at"] < other["posted_at"]):
                other["posted_at"] = b["posted_at"]
            merged += 1
            continue
        kept[bk] = b
    for j in ats_jobs:
        j.pop("_nt", None)
    return list(kept.values()), merged


def dedupe_by_key(jobs: list[dict]) -> tuple[list[dict], int]:
    """Collapse exact identity-key duplicates (same company, title, location bucket)."""
    out: dict[str, dict] = {}
    dropped = 0
    for j in jobs:
        k = j["key"]
        if k in out:
            dropped += 1
            o = out[k]
            for s in [j["source"]] + j.get("also_on", []):
                if s != o["source"] and s not in o["also_on"]:
                    o["also_on"].append(s)
            if j.get("posted_at") and (not o.get("posted_at") or j["posted_at"] < o["posted_at"]):
                o["posted_at"] = j["posted_at"]
            continue
        out[k] = j
    return list(out.values()), dropped
