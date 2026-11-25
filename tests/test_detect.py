import pytest

from app.detect import (crypto_relevance, geography, parse_salary_text, role_family, seniority, to_usd_year,
                        workplace)

FX = {"USD": 1.0, "EUR": 0.9, "GBP": 0.8, "INR": 80.0, "CHF": 0.9, "HKD": 7.8}


@pytest.mark.parametrize("text,expected", [
    ("Base salary: $120,000 - $150,000 per year", (120000, 150000, "USD", "year")),
    ("€80k–100k", (80000, 100000, "EUR", "year")),
    ("The pay range is USD 150K - 200K", (150000, 200000, "USD", "year")),
    ("$60 - $80/hr", (60, 80, "USD", "hour")),
    ("Salary 6,000 - 8,000 EUR per month", (6000, 8000, "EUR", "month")),
    ("12-18 LPA", (1200000, 1800000, "INR", "year")),
    ("CHF 120'000 - 140'000", (120000, 140000, "CHF", "year")),
    ("₹25,00,000 - ₹35,00,000 per annum", (2500000, 3500000, "INR", "year")),
    ("$110.4K - $220.8K", (110400, 220800, "USD", "year")),
    ("Compensation: £50,000/yr", (50000, 50000, "GBP", "year")),
])
def test_salary_ranges(text, expected):
    s = parse_salary_text(text)
    assert (s["min"], s["max"], s["currency"], s["per"]) == expected


@pytest.mark.parametrize("text", ["We raised $20M in 2024", "Founded 2017 - 2020", "Team of 50 - 80 people", ""])
def test_salary_ignores_non_pay_numbers(text):
    assert parse_salary_text(text) is None


def test_usd_annualisation_and_bounds():
    assert to_usd_year({"min": 60, "max": 80, "currency": "USD", "per": "hour"}, FX) == {"min_usd": 124800, "max_usd": 166400, "mid_usd": 145600}
    assert to_usd_year({"min": 90000, "max": 90000, "currency": "EUR", "per": "year"}, FX)["mid_usd"] == 100000
    assert to_usd_year({"min": 5, "max": 6, "currency": "USD", "per": "year"}, FX) is None  # below sanity floor
    assert to_usd_year({"min": 100, "max": 200, "currency": "XYZ", "per": "year"}, FX) is None


@pytest.mark.parametrize("ats,loc,title,expected", [
    ("remote", "New York", "Engineer", "remote"),
    (None, "Remote - US", "Engineer", "remote"),
    (None, "London (Hybrid)", "Engineer", "hybrid"),
    (None, "Singapore", "Engineer", "onsite"),
    (None, "", "Engineer", "unknown"),
    ("Hybrid", "", "Engineer", "hybrid"),
])
def test_workplace(ats, loc, title, expected):
    assert workplace(ats, loc, title) == expected


@pytest.mark.parametrize("loc,countries,regions", [
    ("Remote - US", ["US"], ["North America"]),
    ("New York, NY", ["US"], ["North America"]),
    ("Austin, TX", ["US"], ["North America"]),
    ("Zug, Switzerland", ["CH"], ["Europe"]),
    ("Singapore / Hong Kong", ["SG", "HK"], ["Asia-Pacific"]),
    ("Remote (EMEA)", [], ["Europe", "Middle East & Africa"]),
    ("Anywhere", [], ["Global"]),
    ("Bengaluru, India", ["IN"], ["Asia-Pacific"]),
    ("Dubai, UAE", ["AE"], ["Middle East & Africa"]),
    ("São Paulo, Brazil", ["BR"], ["Latin America"]),
])
def test_geography(loc, countries, regions):
    c, r = geography(loc)
    assert sorted(c) == sorted(countries)
    assert r == regions


@pytest.mark.parametrize("title,level", [
    ("Senior Software Engineer", "Senior"), ("Sr. Backend Engineer", "Senior"), ("Staff Protocol Engineer", "Staff+"),
    ("Engineering Manager, Wallet", "Manager"), ("Head of Growth", "Director"), ("VP of Finance", "Executive"),
    ("Chief Technology Officer", "Executive"), ("Software Engineering Intern", "Intern"), ("Junior Analyst", "Entry"),
    ("Backend Engineer", "Mid"), ("Associate General Counsel", "Mid"), ("Product Manager, Payments", "Mid"),
])
def test_seniority(title, level):
    assert seniority(title) == level


@pytest.mark.parametrize("title,family", [
    ("Senior Software Engineer", "Engineering"), ("Security Engineer", "Security"), ("Smart Contract Auditor", "Security"),
    ("Data Engineer", "Data & Research"), ("Product Designer", "Design"), ("Product Marketing Manager", "Marketing"),
    ("Solutions Engineer", "Sales & BD"), ("Developer Relations Engineer", "Community & Content"),
    ("Compliance Analyst", "Legal & Compliance"), ("FinCrime Analyst", "Legal & Compliance"), ("Quant Researcher", "Trading & Investment"),
    ("Community Manager", "Community & Content"), ("Executive Assistant", "Operations"), ("Customer Support Specialist", "Customer Support"),
    ("Senior Recruiter", "People & Recruiting"), ("Account Executive, Institutional", "Sales & BD"), ("Senior Accountant", "Finance"),
    ("Product Manager, On-Chain Exchange / Trading", "Product"), ("Senior Director, Data Center Design & Engineering", "Engineering"),
])
def test_role_family(title, family):
    assert role_family(title) == family


def test_role_family_falls_back_to_department():
    assert role_family("Specialist", "Legal") == "Legal & Compliance"
    assert role_family("Specialist", None) == "Other"


def test_crypto_relevance():
    assert crypto_relevance("Build DeFi smart contract tooling on Ethereum") >= 3
    assert crypto_relevance("WordPress theme developer") == 0
    assert crypto_relevance("wallet token") == 1.0


def test_strip_html_handles_multiple_escaping():
    from app.text import strip_html
    raw = "&lt;p&gt;Annual base salary range: $212,330 &amp;mdash; $249,800 USD&amp;nbsp;&lt;/p&gt;"
    text = strip_html(raw)
    assert "—" in text and "&" not in text
    assert parse_salary_text(text)["max"] == 249800
