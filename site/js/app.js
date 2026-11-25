/* Role Tape front end. No framework, no build step. Reads data/*.json written by app/sweep.py. */
(function () {
  "use strict";
  // Column order of data/jobs.json rows (see site_job in app/sweep.py)
  const C = { key: 0, company: 1, title: 2, url: 3, source: 4, loc: 5, countries: 6, regions: 7, workplace: 8,
    seniority: 9, family: 10, salary: 11, posted: 12, first: 13, opened: 14, fresh: 15, ghost: 16, isNew: 17,
    newSweep: 18, also: 19, slug: 20, kind: 21, reposts: 22 };
  const FAMILIES = ["Engineering", "Security", "Data & Research", "Product", "Design", "Marketing", "Community & Content",
    "Sales & BD", "Customer Support", "Trading & Investment", "Legal & Compliance", "Finance", "People & Recruiting", "Operations", "Other"];
  const LEVELS = ["Intern", "Entry", "Mid", "Senior", "Staff+", "Manager", "Director", "Executive"];
  const REGIONS = ["North America", "Latin America", "Europe", "Middle East & Africa", "Asia-Pacific", "Global"];
  const WORKPLACES = ["remote", "hybrid", "onsite", "unknown"];
  const BOARD_LABEL = { cryptocurrencyjobs: "Cryptocurrency Jobs", cryptojobslist: "CryptoJobsList", remoteok: "Remote OK", remotive: "Remotive", himalayas: "Himalayas" };
  const ATS_LABEL = { greenhouse: "Greenhouse", lever: "Lever", "lever-eu": "Lever EU", ashby: "Ashby", workable: "Workable", smartrecruiters: "SmartRecruiters", recruitee: "Recruitee" };
  const REPO = "https://github.com/PrafullJ0shi/role-tape";
  const PAGE = 100;

  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") n.className = v; else if (k === "text") n.textContent = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
    }
    for (const k of kids) if (k != null) n.append(k.nodeType ? k : document.createTextNode(k));
    return n;
  };
  const fmt = (n) => (n == null ? "–" : Number(n).toLocaleString("en-US"));
  const signed = (n) => (n == null ? "–" : (n > 0 ? "+" : n < 0 ? "−" : "") + Math.abs(n).toLocaleString("en-US"));
  const k = (n) => (n >= 1e6 ? (n / 1e6).toFixed(2) + "M" : Math.round(n / 1000) + "k");
  const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const day = (iso) => (iso ? `${+iso.slice(8, 10)} ${MONTHS[+iso.slice(5, 7) - 1]}` : "–");
  const sourceLabel = (s) => { const [a, b] = s.split(":"); return a === "board" ? BOARD_LABEL[b] || b : (ATS_LABEL[a] || a); };

  let JOBS = [], COMPANIES = [], HISTORY = null, META = null, FLIPS = [], HEALTH = null;
  let filtered = [], shown = PAGE, cShown = 40, cSort = { k: "H", dir: -1 };

  async function getJSON(p) { const r = await fetch(p, { cache: "no-cache" }); if (!r.ok) throw new Error(p); return r.json(); }

  async function boot() {
    initTheme();
    try {
      const [j, c, h, m, f, hl] = await Promise.all([getJSON("data/jobs.json"), getJSON("data/companies.json"), getJSON("data/history.json"),
        getJSON("data/meta.json"), getJSON("data/flips.json").catch(() => []), getJSON("data/health.json").catch(() => null)]);
      JOBS = j.rows; COMPANIES = c.companies; HISTORY = h; META = m; FLIPS = f; HEALTH = hl;
    } catch (e) {
      $("#stamp").textContent = "Could not load the sweep data. Run python -m app.sweep first.";
      return;
    }
    stamp(); buildFilters(); applyWatchOnLoad(); renderBoard(); renderTrends(); renderFeeds(); renderMethod(); route();
    window.addEventListener("hashchange", route);
  }

  /* ------------------------------------------------------------ routing, theme */
  function route() {
    const v = (location.hash || "#board").slice(1).split("?")[0];
    const view = ["board", "trends", "feeds", "method"].includes(v) ? v : "board";
    document.querySelectorAll("section.view").forEach((s) => s.classList.toggle("on", s.id === "view-" + view));
    document.querySelectorAll("nav.tabs a").forEach((a) => a.toggleAttribute("aria-current", a.dataset.view === view) || a.setAttribute("aria-current", a.dataset.view === view ? "page" : "false"));
    document.querySelectorAll("nav.tabs a").forEach((a) => { if (a.dataset.view === view) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  }
  function initTheme() {
    const saved = localStorage.getItem("rt-theme");
    if (saved) document.documentElement.dataset.theme = saved;
    $("#theme").addEventListener("click", () => {
      const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = cur === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next; localStorage.setItem("rt-theme", next);
    });
  }
  function stamp() {
    const t = META.swept_at.replace("T", " ").replace("Z", " UTC");
    $("#stamp").innerHTML = `Last sweep <b>${t}</b> · <b>${fmt(META.jobs)}</b> open roles at <b>${fmt(META.employers_total)}</b> employers · ` +
      `<b>${fmt(META.companies_ok)}</b> of ${fmt(META.companies)} company boards read · ${fmt(META.boards.filter((b) => b.ok).length)} job boards · next sweep in about 24 h`;
  }

  /* ------------------------------------------------------------ board */
  const F = { q: "", family: "", seniority: "", workplace: "", region: "", country: "", salary: "", source: "", sort: "new", isNew: false, noGhost: false };
  function option(sel, v, label) { sel.append(el("option", { value: v, text: label })); }
  function buildFilters() {
    const count = (idx) => { const m = new Map(); for (const r of JOBS) { const v = r[idx]; (Array.isArray(v) ? v : [v]).forEach((x) => m.set(x, (m.get(x) || 0) + 1)); } return m; };
    const fam = count(C.family), lev = count(C.seniority), wp = count(C.workplace), reg = count(C.regions), cc = count(C.countries);
    const s = (id, all, list, m) => { const sel = $(id); option(sel, "", all); list.filter((x) => m.get(x)).forEach((x) => option(sel, x, `${x} (${fmt(m.get(x))})`)); };
    s("#f-family", "all families", FAMILIES, fam); s("#f-seniority", "all levels", LEVELS, lev);
    s("#f-workplace", "any workplace", WORKPLACES, wp); s("#f-region", "all regions", REGIONS, reg);
    const names = new Intl.DisplayNames(["en"], { type: "region" });
    const ccs = [...cc.keys()].filter(Boolean).sort((a, b) => cc.get(b) - cc.get(a));
    option($("#f-country"), "", "all countries");
    ccs.forEach((c) => { let n = c; try { n = names.of(c); } catch (e) { /* keep code */ } option($("#f-country"), c, `${n} (${fmt(cc.get(c))})`); });
    const bind = (id, key, ev = "change", get = (e) => e.target.value) => $(id).addEventListener(ev, (e) => { F[key] = get(e); shown = PAGE; renderBoard(); });
    bind("#f-q", "q", "input"); bind("#f-family", "family"); bind("#f-seniority", "seniority"); bind("#f-workplace", "workplace");
    bind("#f-region", "region"); bind("#f-country", "country"); bind("#f-salary", "salary"); bind("#f-source", "source"); bind("#f-sort", "sort");
    bind("#f-new", "isNew", "change", (e) => e.target.checked); bind("#f-noghost", "noGhost", "change", (e) => e.target.checked);
    $("#clear").addEventListener("click", () => { setFilters({}); });
    $("#more").addEventListener("click", () => { shown += PAGE; drawRows(); });
    $("#watch-btn").addEventListener("click", saveWatch);
  }
  function setFilters(obj) {
    Object.assign(F, { q: "", family: "", seniority: "", workplace: "", region: "", country: "", salary: "", source: "", sort: "new", isNew: false, noGhost: false }, obj);
    $("#f-q").value = F.q; $("#f-family").value = F.family; $("#f-seniority").value = F.seniority; $("#f-workplace").value = F.workplace;
    $("#f-region").value = F.region; $("#f-country").value = F.country; $("#f-salary").value = F.salary; $("#f-source").value = F.source;
    $("#f-sort").value = F.sort; $("#f-new").checked = F.isNew; $("#f-noghost").checked = F.noGhost;
    shown = PAGE; renderBoard();
  }
  function matches(r, f = F) {
    if (f.family && r[C.family] !== f.family) return false;
    if (f.seniority && r[C.seniority] !== f.seniority) return false;
    if (f.workplace && r[C.workplace] !== f.workplace) return false;
    if (f.region && !r[C.regions].includes(f.region)) return false;
    if (f.country && !r[C.countries].includes(f.country)) return false;
    if (f.source && r[C.kind] !== f.source) return false;
    if (f.salary === "listed" && !r[C.salary]) return false;
    if (f.salary && f.salary !== "listed" && (!r[C.salary] || r[C.salary][1] < +f.salary)) return false;
    if (f.isNew && !r[C.isNew]) return false;
    if (f.noGhost && r[C.ghost] >= 50) return false;
    if (f.q) {
      const hay = (r[C.title] + " " + r[C.company] + " " + r[C.loc]).toLowerCase();
      for (const w of f.q.toLowerCase().split(/\s+/).filter(Boolean)) if (!hay.includes(w)) return false;
    }
    return true;
  }
  function since(r) { return r[C.opened] || r[C.first]; }
  function renderBoard() {
    filtered = JOBS.filter((r) => matches(r));
    const sorters = {
      new: (a, b) => (since(b) || "").localeCompare(since(a) || "") || (b[C.newSweep] - a[C.newSweep]),
      salary: (a, b) => (b[C.salary] ? b[C.salary][1] : -1) - (a[C.salary] ? a[C.salary][1] : -1),
      fresh: (a, b) => b[C.fresh] - a[C.fresh],
      company: (a, b) => a[C.company].localeCompare(b[C.company]) || a[C.title].localeCompare(b[C.title]),
    };
    filtered.sort(sorters[F.sort] || sorters.new);
    figs(); tape(); drawRows(); facets(); feedLink();
  }
  function figs() {
    const n = JOBS.length, sal = JOBS.filter((r) => r[C.salary]).length, rem = JOBS.filter((r) => r[C.workplace] === "remote").length;
    const items = [
      [fmt(n), "open roles"], [fmt(META.opened), "new since previous sweep", META.opened > 0], [fmt(JOBS.filter((r) => r[C.isNew]).length), "new in 3 days"],
      [Math.round((100 * sal) / n) + "%", "publish a salary"], [Math.round((100 * rem) / n) + "%", "remote"], [fmt(META.employers_total), "employers"],
    ];
    const box = $("#figs"); box.replaceChildren(...items.map(([v, kk, acc]) => el("div", {}, el("span", { class: "v" + (acc ? " acc" : ""), text: v }), el("span", { class: "k", text: kk }))));
  }
  function tape() {
    let list = JOBS.filter((r) => r[C.newSweep]);
    let note = null;
    if (!list.length) { list = JOBS.filter((r) => r[C.isNew]); note = META.first_sweep ? "First sweep: showing roles the employers posted in the last three days." : null; }
    list = list.slice().sort((a, b) => (since(b) || "").localeCompare(since(a) || "")).slice(0, 18);
    const ol = $("#tape");
    ol.replaceChildren(...list.map((r) => el("li", {}, el("span", { class: "sq", "aria-label": "new" }),
      el("span", {}, el("a", { href: r[C.url], rel: "noopener", target: "_blank", text: r[C.title] }), " ", el("span", { class: "co", text: "· " + r[C.company] })),
      el("span", { class: "t", text: day(since(r)) }))));
    if (note) ol.before(Object.assign($("#tape-note") || el("p", { id: "tape-note", class: "fig-cap" }), { textContent: note }));
    if (!list.length) ol.replaceChildren(el("li", { text: "No new roles in this window." }));
  }
  function drawRows() {
    const tb = $("#jobs tbody");
    const rows = filtered.slice(0, shown).map((r) => {
      const sal = r[C.salary];
      const where = (r[C.loc] || "—").split(" / ").slice(0, 2).join(" / ");
      const extra = r[C.also].length ? " · also on " + r[C.also].map(sourceLabel).join(", ") : "";
      const tr = el("tr", { class: r[C.ghost] >= 50 ? "stale" : "" },
        el("td", {}, el("span", { class: "sq" + (r[C.isNew] ? "" : " off"), title: r[C.isNew] ? "new in the last 3 days" : "" })),
        el("td", { class: "role" }, el("a", { href: r[C.url], rel: "noopener", target: "_blank", text: r[C.title] }),
          el("span", { class: "sub", text: `${r[C.company]} · ${sourceLabel(r[C.source])}${extra}` })),
        el("td", { class: "hide-m tag", text: r[C.family] }), el("td", { class: "tag", text: r[C.seniority] }),
        el("td", { class: "tag" }, where, el("span", { class: "sub", text: r[C.workplace] + (r[C.regions].length ? " · " + r[C.regions].join(", ") : "") })),
        el("td", { class: "num", title: sal ? sal[2] + " as published" : "not published" }, sal ? `${k(sal[0])}${sal[1] !== sal[0] ? "–" + k(sal[1]) : ""}` : "—", sal && !(sal[2].startsWith("$") && sal[2].endsWith("/yr")) ? el("span", { class: "sub", text: sal[2] }) : null),
        el("td", { class: "num", title: r[C.opened] ? (r[C.posted] ? "posted (ATS)" : "first seen") : "first seen; start date unknown" }, day(since(r)), el("span", { class: "sub", text: r[C.opened] ? (r[C.posted] ? "posted" : "first seen") : "seen ≤" })),
        el("td", { class: "num hide-m", text: Math.round(r[C.fresh]) }),
        el("td", { class: "num hide-m", text: Math.round(r[C.ghost]), title: r[C.reposts] ? `reposted ${r[C.reposts]}×` : "" }));
      return tr;
    });
    tb.replaceChildren(...rows);
    $("#count").textContent = `Showing ${fmt(Math.min(shown, filtered.length))} of ${fmt(filtered.length)} roles` + (filtered.length !== JOBS.length ? ` (filtered from ${fmt(JOBS.length)})` : "");
    $("#more").parentElement.style.display = shown < filtered.length ? "" : "none";
  }
  function facets() {
    const draw = (id, list, idx, key) => {
      const m = new Map(); for (const r of filtered) { const v = r[idx]; (Array.isArray(v) ? v : [v]).forEach((x) => m.set(x, (m.get(x) || 0) + 1)); }
      const max = Math.max(1, ...m.values());
      $(id).replaceChildren(...list.filter((x) => m.get(x)).sort((a, b) => m.get(b) - m.get(a)).map((x) => {
        const li = el("li", { class: F[key] === x ? "on" : "", title: "Filter: " + x }, el("span", { class: "lbl" }, x, el("span", { class: "bar", style: `width:${(100 * m.get(x)) / max}%` })), el("span", { class: "c", text: fmt(m.get(x)) }));
        li.addEventListener("click", () => { const o = {}; for (const kk of Object.keys(F)) o[kk] = F[kk]; o[key] = F[key] === x ? "" : x; setFilters(o); });
        return li;
      }));
    };
    draw("#facet-family", FAMILIES, C.family, "family"); draw("#facet-region", REGIONS, C.regions, "region"); draw("#facet-workplace", WORKPLACES, C.workplace, "workplace");
  }
  function feedLink() {
    let p = "feed/all.xml";
    if (F.family) p = `feed/family/${slug(F.family)}.xml`; else if (F.region) p = `feed/region/${slug(F.region)}.xml`;
    else if (F.workplace === "remote") p = "feed/remote.xml"; else if (F.salary) p = "feed/salary.xml";
    $("#filter-feed").href = p; $("#filter-feed").textContent = "Atom feed: " + p.replace("feed/", "");
  }
  function saveWatch() {
    const w = { f: { ...F }, last: META.swept_at };
    localStorage.setItem("rt-watch", JSON.stringify(w));
    $("#watch-note").classList.add("on");
    $("#watch-note").textContent = "Filter saved in this browser. Next visit, the board opens on it and counts roles that are new since today.";
  }
  function applyWatchOnLoad() {
    let w = null; try { w = JSON.parse(localStorage.getItem("rt-watch") || "null"); } catch (e) { w = null; }
    if (!w) return;
    setFilters(w.f);
    const fresh = JOBS.filter((r) => matches(r, w.f) && r[C.first] > (w.last || "").slice(0, 10)).length;
    const note = $("#watch-note"); note.classList.add("on");
    note.replaceChildren(el("span", { class: "sq" }), ` Watching your saved filter: ${fmt(fresh)} matching role${fresh === 1 ? "" : "s"} new since your last visit (${(w.last || "").slice(0, 10)}). `,
      el("button", { class: "linkbtn", type: "button", onclick: () => { localStorage.removeItem("rt-watch"); note.classList.remove("on"); setFilters({}); } }, "Stop watching"));
    w.last = META.swept_at; localStorage.setItem("rt-watch", JSON.stringify(w));
  }

  /* ------------------------------------------------------------ svg helpers */
  const NS = "http://www.w3.org/2000/svg";
  function svg(w, h, cls = "") { const s = document.createElementNS(NS, "svg"); s.setAttribute("viewBox", `0 0 ${w} ${h}`); s.setAttribute("width", "100%"); s.setAttribute("preserveAspectRatio", "none"); if (cls) s.setAttribute("class", cls); s.style.maxHeight = h + "px"; return s; }
  function sv(tag, attrs, text) { const n = document.createElementNS(NS, tag); for (const [a, v] of Object.entries(attrs)) n.setAttribute(a, v); if (text != null) n.textContent = text; return n; }
  function sparkline(vals, acc) {
    const w = 80, h = 18, s = svg(w, h); s.setAttribute("width", w); s.setAttribute("height", h); s.style.maxHeight = ""; s.setAttribute("role", "img");
    const max = Math.max(1, ...vals), n = vals.length;
    const pts = vals.map((v, i) => [(i * (w - 3)) / Math.max(1, n - 1) + 1, h - 2 - (v / max) * (h - 4)]);
    s.append(sv("polyline", { class: "ln", points: pts.map((p) => p.join(",")).join(" ") }));
    const last = pts[pts.length - 1]; s.append(sv("circle", { class: "dot" + (acc ? " acc" : ""), cx: last[0], cy: last[1], r: 1.6 }));
    s.setAttribute("aria-label", "weekly opens: " + vals.join(", "));
    return s;
  }
  function weeklyOpens(rows, weeks) {
    const now = new Date(META.swept_at), out = new Array(weeks).fill(0);
    for (const r of rows) {
      const d = r[C.opened] || r[C.posted]; if (!d) continue;
      const age = Math.floor((now - new Date(d + "T00:00:00Z")) / 864e5 / 7);
      if (age >= 0 && age < weeks) out[weeks - 1 - age]++;
    }
    return out;
  }
  function barsH(fig, title, caption, entries) {
    const w = 520, rowH = 18, h = entries.length * rowH + 8, s = svg(w, h); s.style.maxHeight = h + "px";
    const max = Math.max(1, ...entries.map((e) => e[1]));
    entries.forEach(([lab, v], i) => {
      const y = i * rowH + 4;
      s.append(sv("text", { x: 0, y: y + 11 }, lab));
      s.append(sv("rect", { class: "bar", x: 170, y: y + 5, width: Math.max(1, ((w - 230) * v) / max), height: 6 }));
      s.append(sv("text", { x: w, y: y + 11, "text-anchor": "end" }, fmt(v)));
    });
    fig.replaceChildren(s, el("figcaption", {}, el("b", { text: title }), " " + caption));
  }

  /* ------------------------------------------------------------ trends */
  function renderTrends() {
    const sweeps = HISTORY.sweeps, last = sweeps[sweeps.length - 1];
    const days = sweeps.length;
    const st = last.states || {};
    $("#trend-lede").textContent = days < 7
      ? `History starts ${sweeps[0].d}. With ${days} daily sweep${days === 1 ? "" : "s"} so far, momentum leans on posting dates and on how each company compares with the rest; the own-history half of the score fills in over the next two weeks.`
      : `${days} daily sweeps since ${sweeps[0].d}. Hiring Momentum blends each company’s own history with today’s cross-section.`;
    const items = [[fmt(st.HIRING || 0), "hiring", true], [fmt(st.STEADY || 0), "steady"], [fmt(st.COOLING || 0), "cooling"], [fmt(st.FROZEN || 0), "frozen"], [fmt(st["CHECK-BOARD"] || 0), "check board"],
      [signed(last.opened - last.closed), "net roles, last sweep"]];
    $("#trend-figs").replaceChildren(...items.map(([v, kk, acc]) => el("div", {}, el("span", { class: "v" + (acc ? " acc" : ""), text: v }), el("span", { class: "k", text: kk }))));
    figOpen(sweeps); figBackfill(); companiesTable(); multiples(); figMix(); flips();
    document.querySelectorAll("#companies th.sortable").forEach((th) => th.addEventListener("click", () => {
      const kk = th.dataset.k; cSort = { k: kk, dir: cSort.k === kk ? -cSort.dir : (kk === "name" || kk === "state" ? 1 : -1) }; companiesTable();
    }));
    $("#c-state").addEventListener("change", companiesTable); $("#c-q").addEventListener("input", companiesTable);
    $("#cmore").addEventListener("click", () => { cShown = 1e9; companiesTable(); });
  }
  function figOpen(sweeps) {
    const fig = $("#fig-open"), w = 560, h = 170, padL = 44, padB = 22, s = svg(w, h);
    const vals = sweeps.map((x) => x.open), max = Math.max(...vals) * 1.1 || 1, n = sweeps.length;
    const X = (i) => padL + (n === 1 ? (w - padL) / 2 : (i * (w - padL - 8)) / (n - 1)), Y = (v) => h - padB - (v / max) * (h - padB - 10);
    s.append(sv("line", { class: "ax", x1: padL, x2: w, y1: h - padB, y2: h - padB }));
    [0, 0.5, 1].forEach((t) => s.append(sv("text", { x: padL - 6, y: Y(max * t / 1.1) + 3, "text-anchor": "end" }, fmt(Math.round(max * t / 1.1)))));
    if (n > 1) s.append(sv("polyline", { class: "ln", points: vals.map((v, i) => `${X(i)},${Y(v)}`).join(" ") }));
    sweeps.forEach((x, i) => {
      const bw = Math.max(2, Math.min(10, (w - padL) / n / 3));
      const sc = (h - padB - 10) / Math.max(1, ...sweeps.map((q) => Math.max(q.opened, q.closed))) * 0.35;
      if (x.opened) s.append(sv("rect", { class: "bar acc", x: X(i) - bw - 1, y: h - padB - x.opened * sc, width: bw, height: x.opened * sc }));
      if (x.closed) s.append(sv("rect", { class: "bar hollow", x: X(i) + 1, y: h - padB - x.closed * sc, width: bw, height: x.closed * sc }));
    });
    s.append(sv("circle", { class: "dot", cx: X(n - 1), cy: Y(vals[n - 1]), r: 2.5 }));
    s.append(sv("text", { x: Math.min(X(n - 1) + 6, w - 60), y: Y(vals[n - 1]) - 6 }, fmt(vals[n - 1])));
    s.append(sv("text", { x: padL, y: h - 6 }, sweeps[0].d)); if (n > 1) s.append(sv("text", { x: w, y: h - 6, "text-anchor": "end" }, sweeps[n - 1].d));
    fig.replaceChildren(s, el("figcaption", {}, el("b", { text: "Figure 1." }), ` Open roles per daily sweep (line), with roles opened (solid) and closed (hollow) by the sweep. ${n === 1 ? "One sweep so far: the line starts tomorrow." : ""}`));
  }
  function figBackfill() {
    const fig = $("#fig-backfill"), weeks = 26, vals = weeklyOpens(JOBS.filter((r) => r[C.kind] === "ats"), weeks);
    const w = 560, h = 170, padL = 44, padB = 22, s = svg(w, h), max = Math.max(1, ...vals) * 1.1, bw = (w - padL) / weeks;
    s.append(sv("line", { class: "ax", x1: padL, x2: w, y1: h - padB, y2: h - padB }));
    [0, 0.5, 1].forEach((t) => s.append(sv("text", { x: padL - 6, y: h - padB - (t / 1.1) * (h - padB - 10) + 3, "text-anchor": "end" }, fmt(Math.round(max * t / 1.1)))));
    vals.forEach((v, i) => s.append(sv("rect", { class: "bar" + (i === weeks - 1 ? " acc" : ""), x: padL + i * bw + 1, y: h - padB - (v / max) * (h - padB - 10), width: bw - 3, height: (v / max) * (h - padB - 10) })));
    s.append(sv("text", { x: padL, y: h - 6 }, `${weeks} weeks ago`)); s.append(sv("text", { x: w, y: h - 6, "text-anchor": "end" }, "this week"));
    fig.replaceChildren(s, el("figcaption", {}, el("b", { text: "Figure 2." }), ` Still-open company-board roles by the week the employer posted them. Roles that already closed are missing, so older weeks read low (survivorship); this is a backfill, not a hiring rate.`));
  }
  function companiesTable() {
    const stf = $("#c-state").value, q = $("#c-q").value.toLowerCase();
    const byCo = new Map(); for (const r of JOBS) { if (r[C.kind] !== "ats") continue; (byCo.get(r[C.slug]) || byCo.set(r[C.slug], []).get(r[C.slug])).push(r); }
    let list = COMPANIES.filter((c) => (!stf || c.state === stf) && (!q || c.name.toLowerCase().includes(q)));
    const key = cSort.k, dir = cSort.dir;
    list.sort((a, b) => { const x = a[key], y = b[key]; if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1; return (typeof x === "string" ? x.localeCompare(y) : x - y) * dir; });
    $("#ccount").textContent = `${fmt(list.length)} companies` + (stf || q ? ` (of ${fmt(COMPANIES.length)})` : "");
    const tb = $("#companies tbody");
    tb.replaceChildren(...list.slice(0, cShown).map((c) => {
      const H = c.H || 0, wpx = Math.min(32, Math.abs(H) * 0.32);
      const hb = el("span", { class: "hbar", "aria-hidden": "true" }, el("i", { class: H >= 0 ? "pos" : "", style: `left:${H >= 0 ? 32 : 32 - wpx}px;width:${wpx}px` }));
      const topFam = Object.keys(c.families || {})[0] || "—";
      return el("tr", {},
        el("td", { class: "role" }, el("a", { href: c.board, rel: "noopener", target: "_blank", text: c.name }), el("span", { class: "sub", text: (ATS_LABEL[c.ats] || c.ats) + (c.kind === "recruiter" ? " · recruiter" : "") + (c.median_salary_usd ? ` · median ${k(c.median_salary_usd)}` : "") })),
        el("td", {}, el("span", { class: "state " + c.state, text: c.state })),
        el("td", { class: "num" }, hb, " " + (H > 0 ? "+" : "") + H.toFixed(0)),
        el("td", { class: "num", text: fmt(c.open) }),
        el("td", {}, sparkline(weeklyOpens(byCo.get(c.slug) || [], 9), c.state === "HIRING")),
        el("td", { class: "num", text: fmt(c.new_7d) }), el("td", { class: "num", text: fmt(c.closed_7d) }),
        el("td", { class: "num", text: signed(c.net_30d) }), el("td", { class: "num", text: signed(c.delta_7d) }), el("td", { class: "num", text: signed(c.delta_30d) }),
        el("td", { class: "num", text: c.days_since_new == null ? "–" : fmt(c.days_since_new) }), el("td", { class: "tag", text: topFam }));
    }));
    $("#cmore").parentElement.style.display = cShown < list.length ? "" : "none";
  }
  function multiples() {
    const weeks = 12;
    const byCo = new Map(); for (const r of JOBS) { if (r[C.kind] !== "ats") continue; (byCo.get(r[C.slug]) || byCo.set(r[C.slug], []).get(r[C.slug])).push(r); }
    const top = COMPANIES.filter((c) => c.ok && c.open >= 3).sort((a, b) => b.H - a.H).slice(0, 12);
    const series = top.map((c) => weeklyOpens(byCo.get(c.slug) || [], weeks));
    const max = Math.max(1, ...series.flat());
    $("#multiples").replaceChildren(...top.map((c, i) => {
      const w = 220, h = 54, s = svg(w, h), vals = series[i], bw = w / weeks;
      vals.forEach((v, j) => s.append(sv("rect", { class: "bar" + (j === weeks - 1 ? " acc" : ""), x: j * bw + 1, y: h - 2 - (v / max) * (h - 6), width: bw - 3, height: Math.max(0.5, (v / max) * (h - 6)) })));
      s.append(sv("line", { class: "ax", x1: 0, x2: w, y1: h - 1.5, y2: h - 1.5 }));
      return el("div", { class: "m" }, el("div", { class: "name" }, el("span", { text: c.name }), el("span", { class: "mono", text: `H ${c.H > 0 ? "+" : ""}${Math.round(c.H)} · ${c.open} open` })), s);
    }));
    $("#mult-cap").innerHTML = `<b>Figure 3.</b> Weekly opens (by employer posting date) over ${weeks} weeks for the twelve companies with the highest Hiring Momentum and at least three open roles. Same y-scale in every panel (max ${max} a week); the accent bar is this week.`;
  }
  function figMix() {
    const fam = new Map(), reg = new Map();
    for (const r of JOBS) { fam.set(r[C.family], (fam.get(r[C.family]) || 0) + 1); r[C.regions].forEach((x) => reg.set(x, (reg.get(x) || 0) + 1)); }
    barsH($("#fig-family"), "Figure 4.", "Open roles by role family, all sources.", [...fam.entries()].sort((a, b) => b[1] - a[1]));
    barsH($("#fig-region"), "Figure 5.", "Open roles by region. A role open to several regions counts in each; remote with no stated place is Global.", [...reg.entries()].sort((a, b) => b[1] - a[1]));
  }
  function flips() {
    const tb = $("#flips tbody");
    if (!FLIPS.length) { tb.replaceChildren(el("tr", {}, el("td", { colspan: 5, class: "tag", text: "No state changes yet. They start with the second sweep." }))); return; }
    tb.replaceChildren(...FLIPS.slice(0, 30).map((f) => el("tr", {}, el("td", { class: "tag", text: f.at.replace("T", " ").slice(0, 16) }), el("td", { text: f.company }),
      el("td", {}, el("span", { class: "state " + f.from, text: f.from })), el("td", {}, el("span", { class: "state " + f.to, text: f.to })), el("td", { class: "tag", text: f.why }))));
  }

  /* ------------------------------------------------------------ feeds, health, method */
  function renderFeeds() {
    const base = location.href.split("#")[0].replace(/index\.html$/, "");
    const cnt = (fn) => JOBS.filter((r) => (r[C.opened]) && fn(r)).length;
    const rows = [["All new roles", "feed/all.xml", cnt(() => true)]];
    FAMILIES.forEach((f) => { const n = cnt((r) => r[C.family] === f); if (n) rows.push([f, `feed/family/${slug(f)}.xml`, n]); });
    REGIONS.forEach((g) => rows.push([`Region: ${g}`, `feed/region/${slug(g)}.xml`, cnt((r) => r[C.regions].includes(g))]));
    rows.push(["Remote roles", "feed/remote.xml", cnt((r) => r[C.workplace] === "remote")]);
    rows.push(["Roles with a published salary", "feed/salary.xml", cnt((r) => r[C.salary])]);
    rows.push(["Company state changes (hiring, cooling, frozen)", "feed/flips.xml", FLIPS.length]);
    $("#feedlist tbody").replaceChildren(...rows.map(([n, p, c]) => el("tr", {}, el("td", {}, el("a", { href: p, text: n })), el("td", { class: "num", text: fmt(Math.min(c, 200)) }), el("td", {}, el("code", { text: base + p })))));
    $("#gh-alerts-link").replaceChildren("Issues: ", el("a", { href: `${REPO}/issues?q=is%3Aissue+is%3Aopen+label%3Aalerts`, text: "open alert issues" }), ". Want a family or region that is missing? Open an issue titled “Alerts: …”.");
    const terms = { cryptocurrencyjobs: "public RSS; robots allows; link back", cryptojobslist: "public RSS; link back", remoteok: "API terms: link back, name Remote OK", remotive: "≤ 4 calls a day, link back, name Remotive; 24 h delay", himalayas: "public API; link back" };
    $("#board-health tbody").replaceChildren(...META.boards.map((b) => el("tr", {}, el("td", {}, el("a", { href: b.home, text: b.label })), el("td", { class: "tag", text: b.ok ? "ok" : "failed: " + (b.error || "") }),
      el("td", { class: "num", text: fmt(b.items) }), el("td", { class: "num", text: fmt(b.kept) }), el("td", { class: "tag", text: terms[b.board] || "" }))));
    const failed = HEALTH ? HEALTH.ats.filter((h) => !h.ok) : [];
    const empty = HEALTH ? HEALTH.ats.filter((h) => h.ok && h.jobs === 0).length : 0;
    $("#ats-health").textContent = `Company boards: ${fmt(META.companies_ok)} read, ${fmt(META.companies_failed)} failed, ${fmt(empty)} read but empty. Failed boards are listed below and never count as closes.`;
    $("#ats-failed tbody").replaceChildren(...(failed.length ? failed.map((h) => el("tr", {}, el("td", { text: h.company }), el("td", { class: "tag", text: ATS_LABEL[h.ats] || h.ats }), el("td", { class: "tag", text: h.error || "" })))
      : [el("tr", {}, el("td", { colspan: 3, class: "tag", text: "None this sweep." }))]));
  }
  function renderMethod() {
    const rows = Object.entries(META.by_source).sort((a, b) => b[1] - a[1]);
    $("#source-table tbody").replaceChildren(...rows.map(([s, n]) => el("tr", {}, el("td", { text: s.startsWith("board:") ? BOARD_LABEL[s.slice(6)] || s : (ATS_LABEL[s] || s) + " API" }), el("td", { class: "num", text: fmt(n) }))));
    $("#foot-sources").innerHTML = "Job board listings via " + META.boards.map((b) => `<a href="${b.home}">${b.label}</a>`).join(", ") +
      ". Company listings via the public job-board APIs of Greenhouse, Lever, Ashby, Workable, SmartRecruiters and Recruitee. FX: " + META.fx + ".";
  }

  boot();
})();
