# Changelog

## 0.1.0 (2026-11-25)

First version.

- Daily sweep of 199 company job boards through official ATS APIs (Greenhouse, Lever, Ashby, Workable,
  SmartRecruiters, Recruitee) and five public job-board feeds (Cryptocurrency Jobs, CryptoJobsList,
  Remote OK, Remotive, Himalayas).
- One schema for every role; canonical URLs; identity-key and cross-source de-duplication.
- Detection of salary (ranges, currencies, periods, USD/yr at the ECB rate), workplace, country and region,
  level and role family.
- Opened / closed / reposted diff that never closes roles on a failed board.
- Hiring Momentum score, freeze detector, freshness and ghost-job score.
- Static site: Board, Trends, Feeds & alerts, Method. Atom feeds per family, region, remote, salary and
  company state changes; GitHub issue alerts; saved filter in the browser.
