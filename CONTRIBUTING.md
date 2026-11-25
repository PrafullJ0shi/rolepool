# Contributing

Small, focused pull requests are welcome.

## Add a company

1. Find its public board on Greenhouse, Lever, Ashby, Workable, SmartRecruiters or Recruitee.
2. Add a row to `data/companies.yml`: `name`, `ats`, `token`, `kind: company`, `origin: manual`.
   For a company that is only partly crypto (a broker, a payments firm), add `filter: crypto`.
3. Check that the board answers (replace `ashby` and `token`):
   `python -c "from app.http import Client; from app.sources.ats import ADAPTERS; print(len(ADAPTERS['ashby'](Client(), 'token')[0]))"`

## Add a job board

Only boards that publish an RSS feed or a public API, and whose terms allow reuse with a link back.
Write the fetcher in `app/sources/boards.py`, add the terms to the module docstring, and add a fixture test.
No HTML scraping of pages, no logins, no API keys.

## Change a rule or formula

Every rule lives in `app/detect.py` or `app/scoring.py` and every threshold in `app/config.py`.
Change the test first (`tests/`), then the code, then the Method text in `site/index.html` and the README.

## Checks

```bash
python -m pytest
```

Tests use recorded fixtures and never touch the network.
