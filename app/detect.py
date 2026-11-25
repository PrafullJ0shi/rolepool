"""Detectors: crypto relevance, salary, workplace, geography, seniority and role family.

All rules are explicit regex tables so they can be read, tested and argued with.
Where the ATS sent a structured field it wins over anything parsed from text.
"""
from __future__ import annotations

import re

from . import config
from .geo import _ALIAS, CITIES, REGION_OF, REGION_WORDS, US_STATE_CODES, US_STATES

# ------------------------------------------------------------------ relevance
_STRONG = ["crypto", "blockchain", "web3", "defi", "stablecoin", "bitcoin", "ethereum", "solana", "onchain",
           "on-chain", "smart contract", "digital asset", "nft", "dao", "staking", "validator", "zero-knowledge",
           "zk-", "zkp", "evm", "solidity", "layer 2", "rollup", "tokeniz", "decentralized", "decentralised",
           "cryptocurrency", "lightning network", "custody of digital", "self-custody", "memecoin", "altcoin"]
_WEAK = ["wallet", "token", "protocol", "exchange", "ledger", "mining", "hash", "dex", "l2", "rust"]
_STRONG_RE = re.compile("|".join(re.escape(k) for k in _STRONG), re.I)
_WEAK_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in _WEAK) + r")s?\b", re.I)


def crypto_relevance(text: str) -> float:
    """Distinct strong keywords count 1, distinct weak keywords 0.5."""
    if not text:
        return 0.0
    strong = {m.group(0).lower() for m in _STRONG_RE.finditer(text)}
    weak = {m.group(1).lower() for m in _WEAK_RE.finditer(text)}
    return len(strong) + 0.5 * len(weak)


# ------------------------------------------------------------------ salary
FX_FALLBACK = {  # units of currency per 1 USD; used only when the ECB feed is unreachable
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "CHF": 0.88, "CAD": 1.38, "AUD": 1.52, "SGD": 1.34, "HKD": 7.8,
    "JPY": 152.0, "INR": 84.0, "AED": 3.67, "PLN": 4.0, "SEK": 10.6, "NOK": 10.9, "DKK": 6.9, "BRL": 5.6,
    "MXN": 19.5, "KRW": 1380.0, "CZK": 23.2, "TRY": 34.0, "ILS": 3.7, "NZD": 1.66, "ZAR": 18.0, "HUF": 360.0,
    "RON": 4.6, "PHP": 58.0, "THB": 34.0, "IDR": 15800.0, "MYR": 4.5, "CNY": 7.2,
}
_SYM = {"US$": "USD", "$": "USD", "€": "EUR", "£": "GBP", "C$": "CAD", "CA$": "CAD", "A$": "AUD", "AU$": "AUD",
        "S$": "SGD", "HK$": "HKD", "¥": "JPY", "₹": "INR", "R$": "BRL", "₩": "KRW", "₪": "ILS", "NZ$": "NZD",
        "zł": "PLN", "CHF": "CHF", "Fr.": "CHF"}
_CODES = sorted(set(FX_FALLBACK) | {"RS", "RS."}, key=len, reverse=True)
_CUR = r"(?:US\$|CA\$|AU\$|NZ\$|HK\$|C\$|A\$|S\$|R\$|\$|€|£|¥|₹|₩|₪|" + "|".join(c for c in FX_FALLBACK) + r")"
_NUM = r"(?:\d{1,2}(?:,\d{2})+,\d{3}|\d{1,3}(?:[,.\u00a0 ']\d{3})+|\d+(?:\.\d+)?)"
_AMT = r"(?:(?P<@c1>" + _CUR + r")\s?)?(?P<@n>" + _NUM + r")\s?(?P<@k>[kKmM](?![a-zA-Z]))?(?:\s?(?P<@c2>" + _CUR + r")(?![a-zA-Z]))?"
_RANGE = re.compile(_AMT.replace("@", "a") + r"\s?(?:-|–|—|to|and)\s?" + _AMT.replace("@", "b"))
_SINGLE = re.compile(_AMT.replace("@", "a"))
_LPA = re.compile(r"(?P<a>\d+(?:\.\d+)?)\s?(?:-|–|to)\s?(?P<b>\d+(?:\.\d+)?)\s?(?:LPA|lpa|lakhs?)")
_CONTEXT = re.compile(r"salary|compensation|base pay|pay range|pay rate|ote\b|per annum|annual|/yr|/year|per year|base range|remuneration|gross", re.I)
_PER = [("hour", re.compile(r"/\s?h(?:ou)?r|per hour|hourly|an hour|/h\b", re.I)),
        ("day", re.compile(r"/\s?day|per day|daily rate", re.I)),
        ("week", re.compile(r"/\s?w(?:ee)?k|per week|weekly", re.I)),
        ("month", re.compile(r"/\s?mo(?:nth)?|per month|monthly|a month|p\.m\.", re.I)),
        ("year", re.compile(r"/\s?y(?:ea)?r|per year|annual|annually|per annum|p\.a\.|a year|yearly", re.I))]
PER_FACTOR = {"hour": 2080, "day": 260, "week": 52, "month": 12, "year": 1}


def _num(s: str, k: str | None) -> float:
    s = s.replace("\u00a0", "").replace(" ", "").replace("'", "")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
        s = re.sub(r"[.,]", "", s)
    else:
        s = s.replace(",", "")
    v = float(s)
    if k and k.lower() == "k":
        v *= 1_000
    elif k and k.lower() == "m":
        v *= 1_000_000
    return v


def _cur(tok: str | None) -> str | None:
    if not tok:
        return None
    t = tok.strip()
    if t in _SYM:
        return _SYM[t]
    t = t.upper()
    return t if t in FX_FALLBACK else None


def parse_salary_text(text: str, default_cur: str | None = None) -> dict | None:
    """Find the first plausible pay range in text. Returns {min,max,currency,per} or None."""
    if not text:
        return None
    m = _LPA.search(text)
    if m:
        return {"min": float(m.group("a")) * 100_000, "max": float(m.group("b")) * 100_000, "currency": "INR", "per": "year"}
    for m in _RANGE.finditer(text):
        cur = _cur(m.group("ac1")) or _cur(m.group("bc1")) or _cur(m.group("ac2")) or _cur(m.group("bc2"))
        if not cur:
            continue
        ka, kb = m.group("ak"), m.group("bk")
        if kb and not ka:
            ka = kb
        try:
            lo, hi = _num(m.group("an"), ka), _num(m.group("bn"), kb)
        except ValueError:
            continue
        if lo <= 0 or hi < lo or hi > lo * 4:
            continue
        window = text[max(0, m.start() - 80): m.end() + 60]
        per = _infer_per(window, hi, cur)
        if per is None:
            continue
        return {"min": lo, "max": hi, "currency": cur, "per": per}
    for m in _SINGLE.finditer(text):
        cur = _cur(m.group("ac1")) or _cur(m.group("ac2"))
        if not cur:
            continue
        window = text[max(0, m.start() - 80): m.end() + 60]
        if not _CONTEXT.search(window):
            continue
        try:
            v = _num(m.group("an"), m.group("ak"))
        except ValueError:
            continue
        per = _infer_per(window, v, cur)
        if per and v > 0:
            return {"min": v, "max": v, "currency": cur, "per": per}
    return None


def _infer_per(window: str, hi: float, cur: str) -> str | None:
    tail = window
    for per, rx in _PER:
        if rx.search(tail):
            return per
    usd = hi / FX_FALLBACK.get(cur, 1.0)
    if usd >= 15_000:
        return "year"
    if 10 <= usd < 300 and _CONTEXT.search(window):
        return "hour"
    return None


def to_usd_year(sal: dict | None, fx: dict) -> dict | None:
    """Annualise and convert to USD. Returns {min_usd, max_usd, mid_usd} or None if outside sanity bounds."""
    if not sal or not sal.get("currency"):
        return None
    rate = fx.get(sal["currency"]) or FX_FALLBACK.get(sal["currency"])
    if not rate:
        return None
    f = PER_FACTOR.get(sal.get("per") or "year", 1)
    lo = float(sal.get("min") or sal.get("max") or 0) * f / rate
    hi = float(sal.get("max") or sal.get("min") or 0) * f / rate
    if lo <= 0:
        return None
    mid = (lo + hi) / 2
    if not (config.SALARY_MIN_USD <= mid <= config.SALARY_MAX_USD):
        return None
    return {"min_usd": round(lo, -2), "max_usd": round(hi, -2), "mid_usd": round(mid, -2)}


# ------------------------------------------------------------------ workplace
_REMOTE = re.compile(r"\bremote\b|\banywhere\b|\bworldwide\b|\bdistributed\b|work from home|\bwfh\b|remote-first|fully remote", re.I)
_HYBRID = re.compile(r"\bhybrid\b", re.I)
_ONSITE = re.compile(r"\bon-?site\b|\bin[- ]office\b|\bin person\b", re.I)


def workplace(ats_value: str | None, location: str, title: str, description: str = "") -> str:
    v = (ats_value or "").lower().replace("_", "").replace("-", "")
    if v in ("remote",):
        return "remote"
    if v in ("hybrid",):
        return "hybrid"
    if v in ("onsite", "inoffice", "office"):
        return "onsite"
    head = f"{title} | {location}"
    if _HYBRID.search(head):
        return "hybrid"
    if _REMOTE.search(head):
        return "remote"
    if _ONSITE.search(head):
        return "onsite"
    if location.strip():
        return "onsite"
    if description and re.search(r"fully remote|100% remote|remote-first|work remotely from anywhere", description, re.I):
        return "remote"
    return "unknown"


# ------------------------------------------------------------------ geography
_ALIAS_RE = {}
for _alias, _code in list(_ALIAS.items()) + list(CITIES.items()):
    if len(_alias) <= 3:
        continue
    _ALIAS_RE[_alias] = (_code, re.compile(r"(?<![a-z])" + re.escape(_alias) + r"(?![a-z])", re.I))
_SHORT = {"US": "US", "USA": "US", "UK": "GB", "UAE": "AE", "NYC": "US", "SF": "US", "KSA": "SA", "BVI": "VG", "U.S.": "US"}
_STATE_RE = re.compile(r",\s*(" + "|".join(sorted(US_STATE_CODES)) + r")\b")
_STATE_NAME_RE = re.compile(r"(?<![a-z])(" + "|".join(sorted(US_STATES, key=len, reverse=True)) + r")(?![a-z])", re.I)
_REGION_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(sorted((re.escape(k) for k in REGION_WORDS if len(k) > 2), key=len, reverse=True)) + r")(?![A-Za-z])", re.I)


def geography(location: str, country_hint: str | None = None) -> tuple[list[str], list[str]]:
    """Return (country codes, regions) for a location string."""
    loc = location or ""
    codes: list[str] = []

    def add(c):
        if c and c not in codes and c in REGION_OF:
            codes.append(c)

    if country_hint:
        h = country_hint.strip()
        add(h.upper() if len(h) == 2 else _ALIAS.get(h.lower()))
    for alias, (code, rx) in _ALIAS_RE.items():
        if rx.search(loc):
            # "Georgia" alone is read as the US state
            add(code)
    for tok in re.split(r"[\s,/;|()\-–]+", loc):
        if tok in _SHORT:
            add(_SHORT[tok])
    if _STATE_RE.search(loc) or _STATE_NAME_RE.search(loc):
        add("US")
    regions: list[str] = []
    for c in codes:
        r = REGION_OF.get(c)
        if r and r not in regions:
            regions.append(r)
    for m in _REGION_RE.finditer(loc):
        for r in REGION_WORDS[m.group(1).lower()]:
            if r not in regions:
                regions.append(r)
    if re.search(r"\bEU\b", loc):
        if "Europe" not in regions:
            regions.append("Europe")
    if not regions and re.search(r"anywhere|worldwide|global|international", loc, re.I):
        regions.append("Global")
    return codes, regions


# ------------------------------------------------------------------ seniority
SENIORITY = ["Intern", "Entry", "Mid", "Senior", "Staff+", "Manager", "Director", "Executive"]
_SEN_RULES = [
    ("Intern", r"\bintern(ship)?\b|\btrainee\b|\bapprentice|\bworking student\b|\bco-?op\b|\bsummer analyst\b"),
    ("Executive", r"\bchief\b|\bc[etfoims]o\b|\bciso\b|\bcfo\b|\bpresident\b|\bvp\b|\bvice president\b|\bsvp\b|\bevp\b|(?<!associate )(?<!assistant )(?<!deputy )\bgeneral counsel\b|\bmanaging director\b|\bgeneral partner\b|\bfounder\b"),
    ("Director", r"\bdirector\b|\bhead of\b|\bhead,|\b\w+ head\b"),
    ("Staff+", r"\bstaff\b|\bprincipal\b|\bdistinguished\b|\bfellow\b|\barchitect\b"),
    ("Manager", r"\b(engineering|team|general|people|department|regional|country|operations|program|delivery|site|area) manager\b|\bmanager of\b|\bteam lead\b|\btech(nical)? lead\b|\blead\b"),
    ("Senior", r"\bsenior\b|\bsr\.?\b|\biii\b|\biv\b|\bexperienced\b"),
    ("Entry", r"\bjunior\b|\bjr\.?\b|\bgraduate\b|\bentry[- ]level\b|\bnew grad\b|\b(analyst|engineer|associate|specialist) i\b|^associate\b(?!.*(director|counsel|partner|vp))"),
    ("Mid", r"\bmid[- ]?(level|senior)?\b|\bintermediate\b|\bii\b"),
]
_SEN_RULES = [(lvl, re.compile(rx, re.I)) for lvl, rx in _SEN_RULES]
_SR_HINT = {"internship": "Intern", "entry level": "Entry", "associate": "Entry", "mid-senior level": "Mid",
            "director": "Director", "executive": "Executive"}


def seniority(title: str, hint: str | None = None) -> str:
    t = title or ""
    for lvl, rx in _SEN_RULES:
        if rx.search(t):
            return lvl
    if hint and hint.lower() in _SR_HINT:
        return _SR_HINT[hint.lower()]
    return "Mid"


# ------------------------------------------------------------------ role family
FAMILIES = ["Engineering", "Security", "Data & Research", "Product", "Design", "Marketing", "Community & Content",
            "Sales & BD", "Customer Support", "Trading & Investment", "Legal & Compliance", "Finance",
            "People & Recruiting", "Operations", "Other"]
_FAM_RULES = [
    # 1. specific titles that would otherwise be caught by a broader rule further down
    ("Security", r"securit|appsec|\bauditor\b|smart contract audit|threat|red team|penetration|\bsoc\b|\bciso\b|incident response"),
    ("Customer Support", r"support|dispute|chargeback|customer service|customer success|customer experience|\bcx\b|help ?desk|onboarding specialist|client service|player experience"),
    ("Sales & BD", r"solutions? engineer|sales engineer|customer engineer|pre-?sales|solutions? architect"),
    ("Community & Content", r"developer relations|devrel|developer advocate|evangelist"),
    ("Data & Research", r"data engineer|data scien|machine learning|\bml engineer|research engineer|research scientist|analytics engineer"),
    ("Product", r"product manager|product owner|product lead|head of product|product director|director of product|vp,? product|chief product"),
    ("Engineering", r"engineer|developer|programmer|devops|\bsre\b|\bcto\b"),
    # 2. broad families
    ("Design", r"designer|\bdesign (lead|director|manager)|head of design|product design|graphic design|brand design|visual design|\bux\b|\bui\b|illustrat|motion|creative|animator|art director|3d artist|video editor"),
    ("Marketing", r"marketing|growth|\bseo\b|\bsem\b|brand|communications|\bcomms\b|public relations|\bpr\b|social media|events?\b|lifecycle|\bcrm\b|campaign|influencer|acquisition|copywrit"),
    ("Community & Content", r"communit|ambassador|content|editor|journalist|reporter|writer|educat|moderator|podcast|producer"),
    ("Legal & Compliance", r"legal|counsel|lawyer|attorney|paralegal|complian|\baml\b|\bkyc\b|\bkyb\b|regulator|risk|fraud|fincrime|sanction|mlro|policy|government|licens|privacy|financial crime|investigat"),
    ("Finance", r"financ|accountant|accounting|controller|\btax\b|treasur|fp&a|internal audit|payroll|bookkeep|\bcfo\b|billing|accounts payable|accounts receivable|reconcil"),
    ("People & Recruiting", r"recruit|talent|people|\bhr\b|human resources|total rewards|compensation & benefits|learning & development|sourcer"),
    ("Sales & BD", r"\bsales\b|business development|\bbd\b|bdr|sdr|account executive|account manager|key account|partnership|partner manager|institutional|relationship manager|listing|\bvip\b|ecosystem|deal|revenue|commercial|go-to-market|\bgtm\b|channel"),
    ("Trading & Investment", r"trader|trading|\bquant|market mak|\botc\b|portfolio|investment|investor|venture|\bcapital markets\b|asset manag|liquidity|derivatives|structured product|execution"),
    ("Data & Research", r"\bdata\b|analytics|analyst|scientist|research|\bai\b|cryptograph|economist|statistic|\bllm\b"),
    ("Product", r"product|program manager|\btpm\b|project manager|scrum|delivery manager"),
    ("Engineering", r"infrastructure|platform|backend|back-end|frontend|front-end|full[- ]?stack|solidity|\brust\b|golang|blockchain|architect|\bqa\b|\btest|mobile|\bios\b|android|firmware|hardware|protocol|smart contract|technical lead|software|\bit\b|systems admin|network|database|\bdba\b|cloud"),
    ("Operations", r"operation|\bops\b|chief of staff|office|executive assistant|assistant|administrat|workplace|procurement|strategy|business analyst|facilit|logistic|supply|vendor|coordinator|\bcoo\b|\bceo\b|general manager"),
]
_FAM_RULES = [(f, re.compile(rx, re.I)) for f, rx in _FAM_RULES]


def role_family(title: str, department: str | None = None) -> str:
    for fam, rx in _FAM_RULES:
        if rx.search(title or ""):
            return fam
    for fam, rx in _FAM_RULES:
        if department and rx.search(department):
            return fam
    return "Other"
