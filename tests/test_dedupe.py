from app.dedupe import (canonical_url, dedupe_by_key, identity_key, jaccard, merge_boards_into_ats, norm_company,
                        norm_title)


def test_canonical_url_strips_tracking():
    u = "http://Jobs.Lever.co/acme/123/?utm_source=x&gh_src=NaN&lever-source=LinkedIn&team=eng#apply"
    assert canonical_url(u) == "https://jobs.lever.co/acme/123?team=eng"
    assert canonical_url("https://boards.greenhouse.io/acme/jobs/1?gh_jid=1&gh_src=abc") == "https://boards.greenhouse.io/acme/jobs/1?gh_jid=1"


def test_norm_company():
    assert norm_company("Kraken, Inc.") == norm_company("kraken.com") == "kraken"
    assert norm_company("Solana Foundation", hard=True) == "solana"
    assert norm_company("Uniswap Labs", hard=True) == norm_company("Uniswap", hard=True)


def test_norm_title():
    assert norm_title("Sr. Backend Eng (Remote, EU)") == "senior backend engineer"
    assert norm_title("Senior Backend Engineer - Remote") == "senior backend engineer"
    assert norm_title("BD & Partnerships Lead") == "business development and partnerships lead"


def test_identity_key_stable_and_location_aware():
    a = identity_key("Kraken", "Senior Backend Engineer", ["US"], "remote")
    b = identity_key("kraken.com", "Sr Backend Engineer (Remote)", ["US"], "remote")
    c = identity_key("Kraken", "Senior Backend Engineer", ["GB"], "remote")
    assert a == b and a != c and len(a) == 16


def _j(company, title, source, kind="ats", key=None, posted=None):
    return {"company": company, "title": title, "source": source, "source_kind": kind, "also_on": [],
            "key": key or identity_key(company, title, [], "remote"), "posted_at": posted}


def test_board_item_merges_into_ats_posting():
    ats = [_j("Uniswap Labs", "Senior Frontend Engineer", "ashby:uniswap")]
    boards = [_j("Uniswap", "Senior Frontend Engineer (Remote)", "board:cryptojobslist", "board"),
              _j("Uniswap", "Head of Legal", "board:cryptojobslist", "board")]
    kept, merged = merge_boards_into_ats(ats, boards)
    assert merged == 1 and len(kept) == 1 and kept[0]["title"] == "Head of Legal"
    assert ats[0]["also_on"] == ["board:cryptojobslist"]


def test_board_duplicates_across_boards_collapse():
    boards = [_j("Acme", "Solidity Engineer", "board:cryptojobslist", "board", posted="2026-11-20T00:00:00Z"),
              _j("Acme", "Solidity Engineer", "board:cryptocurrencyjobs", "board", posted="2026-11-18T00:00:00Z")]
    kept, merged = merge_boards_into_ats([], boards)
    assert merged == 1 and kept[0]["also_on"] == ["board:cryptocurrencyjobs"]
    assert kept[0]["posted_at"] == "2026-11-18T00:00:00Z"


def test_dedupe_by_key_keeps_first_and_earliest_post():
    a = _j("Acme", "Engineer", "greenhouse:acme", posted="2026-11-10T00:00:00Z")
    b = dict(_j("Acme", "Engineer", "greenhouse:acme", posted="2026-11-01T00:00:00Z"), key=a["key"])
    out, dropped = dedupe_by_key([a, b])
    assert dropped == 1 and out[0]["posted_at"] == "2026-11-01T00:00:00Z"


def test_jaccard():
    assert jaccard("senior frontend engineer", "senior frontend engineer") == 1.0
    assert jaccard("a b", "c d") == 0.0
