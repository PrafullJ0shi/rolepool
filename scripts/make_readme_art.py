"""README banner, light and dark, as SVG with the lettering converted to outlines.

GitHub's image proxy loads no web fonts, so ET Book and IBM Plex Mono glyphs are drawn as paths
straight from the site's own font files. The small bar chart is weekly opens from data/jobs.json.
Usage: python scripts/make_readme_art.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "site" / "fonts"
DOCS = ROOT / "docs"

THEMES = {
    "light": {"paper": "#FFFFF8", "ink": "#111111", "ink2": "#4A4A45", "rule": "#D9D7CC", "accent": "#B23A1E"},
    "dark": {"paper": "#151513", "ink": "#E9E7DF", "ink2": "#A9A69C", "rule": "#34332E", "accent": "#E2694B"},
}


def outline(font: TTFont, text: str, size: float, x: float, y: float, track: float = 0.0, anchor: str = "start"):
    gs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm
    s, hmtx = size / upm, font["hmtx"]
    names = [cmap.get(ord(c)) or cmap.get(ord(" ")) for c in text]
    width = sum(hmtx[n][0] * s + track for n in names) - track
    cx = x - (width if anchor == "end" else width / 2 if anchor == "middle" else 0)
    pen = SVGPathPen(gs)
    for n in names:
        gs[n].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
        cx += hmtx[n][0] * s + track
    return pen.getCommands(), width


def weekly(weeks: int = 20):
    data = json.loads((ROOT / "data" / "jobs.json").read_text())
    now = datetime.fromisoformat(data["swept_at"].replace("Z", "+00:00"))
    out = [0] * weeks
    for j in data["jobs"]:
        d = j.get("opened_at")
        if not d or j["source_kind"] != "ats":
            continue
        age = (now - datetime.fromisoformat(d.replace("Z", "+00:00"))).days // 7
        if 0 <= age < weeks:
            out[weeks - 1 - age] += 1
    return out, data


def banner(theme: str, serif, italic, mono, meta, bars) -> str:
    t = THEMES[theme]
    W, H = 1280, 320
    word, ww = outline(serif, "Role Tape", 104, 72, 168)
    sub, _ = outline(italic, "crypto hiring, swept daily from official job feeds", 30, 72, 222)
    strip_txt = (f"{meta['jobs']:,} OPEN ROLES   {meta['employers_total']:,} EMPLOYERS   "
                 f"{meta['companies_ok']} COMPANY BOARDS   {len(meta['boards'])} JOB BOARDS   DAILY SWEEP")
    strip, _ = outline(mono, strip_txt, 15, 72, 284, track=0.6)
    # bar chart, right side
    bx, by, bw, bh = 900, 96, 308, 120
    mx = max(bars) or 1
    step = bw / len(bars)
    rects = []
    for i, v in enumerate(bars):
        h = v / mx * bh
        color = t["accent"] if i == len(bars) - 1 else t["ink"]
        rects.append(f'<rect x="{bx + i * step + 1:.1f}" y="{by + bh - h:.1f}" width="{step - 4:.1f}" height="{h:.1f}" fill="{color}"/>')
    cap, _ = outline(italic, "new roles a week, by posting date", 17, bx, by + bh + 28)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Role Tape: crypto hiring, swept daily from official job feeds">
<rect width="{W}" height="{H}" fill="{t['paper']}"/>
<rect x="72" y="40" width="{W - 144}" height="1.5" fill="{t['ink']}"/>
<path d="{word}" fill="{t['ink']}"/>
<rect x="{72 + ww + 22:.1f}" y="128" width="44" height="4" fill="{t['accent']}"/>
<path d="{sub}" fill="{t['ink2']}"/>
{''.join(rects)}
<rect x="{bx}" y="{by + bh + 1}" width="{bw}" height="1" fill="{t['rule']}"/>
<path d="{cap}" fill="{t['ink2']}"/>
<rect x="72" y="256" width="{W - 144}" height="1" fill="{t['rule']}"/>
<path d="{strip}" fill="{t['ink2']}"/>
</svg>
'''


def main():
    serif = TTFont(FONTS / "et-book-roman.woff")
    italic = TTFont(FONTS / "et-book-italic.woff")
    mono = TTFont(FONTS / "IBMPlexMono-Medium-Latin1.woff2")
    bars, _ = weekly()
    meta = json.loads((ROOT / "data" / "meta.json").read_text())
    for theme in THEMES:
        (DOCS / f"banner-{theme}.svg").write_text(banner(theme, serif, italic, mono, meta, bars))
    print("banners written")


if __name__ == "__main__":
    sys.exit(main())
