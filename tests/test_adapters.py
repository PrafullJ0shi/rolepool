"""Adapters against small recorded payloads, no network."""
import json
from pathlib import Path

from app.sources import ats, boards

FIX = Path(__file__).parent / "fixtures"


class FakeClient:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_json(self, url, params=None):
        for k, v in self.mapping.items():
            if k in url:
                return json.loads((FIX / v).read_text()) if v.endswith(".json") else None
        return None

    def get(self, url, params=None):
        for k, v in self.mapping.items():
            if k in url:
                class R:
                    status_code = 200
                    content = (FIX / v).read_bytes()
                return R()
        return None


def test_greenhouse():
    jobs, err = ats.greenhouse(FakeClient({"greenhouse": "greenhouse.json"}), "acme")
    assert err is None and len(jobs) == 1
    j = jobs[0]
    assert j["title"] == "Senior Protocol Engineer" and j["department"] == "Engineering"
    assert j["posted_at"] == "2026-11-16T19:12:10Z" and "on-chain" in j["description"]


def test_lever_salary_and_workplace():
    jobs, _ = ats.lever(FakeClient({"lever": "lever.json"}), "acme")
    j = jobs[0]
    assert j["salary"] == {"min": 180000, "max": 220000, "currency": "USD", "per": "year"}
    assert j["workplace"] == "hybrid" and j["posted_at"] == "2026-07-29T14:23:26Z"


def test_ashby_compensation_component():
    jobs, _ = ats.ashby(FakeClient({"ashbyhq": "ashby.json"}), "acme")
    assert len(jobs) == 1  # unlisted job skipped
    assert jobs[0]["salary"] == {"min": 110400, "max": 220800, "currency": "USD", "per": "year"}
    assert jobs[0]["workplace"] == "remote"


def test_missing_board_reports_error():
    jobs, err = ats.greenhouse(FakeClient({}), "nope")
    assert jobs is None and err == "no board"


def test_cryptojobslist_rss():
    jobs, err = boards.cryptojobslist(FakeClient({"cryptojobslist": "cryptojobslist.xml"}))
    assert err is None and jobs[0]["company"] == "Chainalysis" and jobs[0]["location"] == "Tel Aviv, Israel"


def test_relevance_gate_for_general_boards():
    keep = {"title": "Solidity Engineer", "department": "", "description": "DeFi protocol on Ethereum"}
    drop = {"title": "WordPress Developer", "department": "", "description": "themes and plugins"}
    assert boards.is_relevant("remotive", keep, 2) and not boards.is_relevant("remotive", drop, 2)
    assert boards.is_relevant("cryptojobslist", drop, 2)  # crypto-native boards are trusted
