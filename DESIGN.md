# DESIGN.md

Written before any page markup. The site is a research plate about crypto hiring, not a job-board landing page. If a choice is not covered here, pick the plainer option.

## 1. Intent

One question per view:

| View | Question it answers |
| :--- | :--- |
| Board | Which crypto roles are open right now, and which ones appeared in the last sweep? |
| Trends | Which companies are adding roles, which are cooling, and which have gone quiet? |
| Feeds | How do I hear about new roles without checking the page every day? |
| Method | How is each number on this site computed, and where can it be wrong? |

The board is the page. Filters and the "new this sweep" list sit in the first viewport. There is no hero, no tagline, no illustration.

## 2. Reference points

- Edward Tufte's printed plates: high data-ink ratio, sparklines inline with text, small multiples, labels on the data instead of legends.
- NASA technical reports: numbered sections, plain captions ("Figure 2. Open roles per sweep, all companies"), tables with right-aligned figures, footnotes for caveats.

Anti-references: SaaS job boards with gradient heroes, three feature cards, avatar stacks, "find your dream role", pill soup, glow, glassmorphism.

## 3. Colour

One accent. Everything else is ink on paper.

| Token | Light | Dark | Use |
| :--- | :--- | :--- | :--- |
| `--paper` | `#FFFFF8` | `#151513` | page ground |
| `--ink` | `#111111` | `#E9E7DF` | text, chart lines |
| `--ink-2` | `#4A4A45` | `#A9A69C` | secondary text, axes |
| `--rule` | `#D9D7CC` | `#34332E` | hairlines, table rules |
| `--wash` | `#F3F2EA` | `#1D1D1A` | zebra rows, inputs |
| `--accent` | `#B23A1E` | `#E2694B` | new this sweep, the one highlighted series, focus ring, links on hover |

Rules:

- The accent marks exactly one idea per view: "new", "selected" or "the series under discussion". Closes and freezes are shown in ink with a hatched or hollow mark, not a second colour.
- No gradients of any kind, no shadows, no glows. Hairlines are 1px `--rule`.
- Charts are monochrome ink with the accent for the highlighted series only.

## 4. Type

Two families, self-hosted, nothing else.

- **ET Book** (MIT): headings, body, captions. The Tufte book face.
- **IBM Plex Mono** (OFL): every number, table figure, code, filters, timestamps. Tabular by design.

Scale (rem, base 16px, ratio about 1.2):

| Token | Size | Line height | Use |
| :--- | ---: | ---: | :--- |
| `--t-xs` | 0.75 | 1.35 | footnotes, axis labels (mono) |
| `--t-sm` | 0.875 | 1.4 | table cells (mono), captions |
| `--t-md` | 1.0625 | 1.5 | body (ET Book) |
| `--t-lg` | 1.375 | 1.3 | section titles |
| `--t-xl` | 2.0 | 1.15 | page title / wordmark |

Section titles are numbered in the report style: `1 Board`, `2 Trends`. Italics (ET Book italic) are used for captions and for the honesty notes. Bold is rare.

## 5. Spacing and grid

Spacing scale: 4, 8, 12, 16, 24, 32, 48, 64 px (`--s1` to `--s8`). No other values.

- Max content width 1240px, left-aligned with a 24px gutter. Prose columns cap at 68ch.
- Board table uses the full width; side notes (Tufte margin notes) sit in a 240px right rail on screens wider than 1100px and fold under the table below that.
- Mobile: one column, the table becomes a stacked list with the same mono figures.

## 6. Components

- **Tabs**: plain text links with a 2px ink underline on the active one. No pills.
- **Filters**: native `<select>` and `<input>` styled flat on `--wash`, mono text, 1px rule border. A "Clear" text button. Active filter count shown as a figure, not a badge.
- **Table**: hairline rules between rows, no vertical rules, figures right-aligned, header in small caps mono. A 6px accent square at row start means "first seen in the last sweep".
- **Sparklines**: 80 x 18 px, 1px ink line, last point as a 2px dot (accent only if the company is flagged hiring), no axes. Min and max shown as tiny mono figures when space allows.
- **Small multiples**: same y-scale within a grid, caption under each.
- **Notes**: margin notes in ET Book italic, `--ink-2`, introduced by a superscript figure.

## 7. Voice

Direct, a little dry. Say what the number is and what it is not.

- "First seen by this sweep", never "posted" unless the ATS sent a posting date, in which case "posted (ATS)".
- Salary appears only when the employer or board published it. Converted figures say "USD/yr, converted at ECB rate of {date}".
- A board that failed is listed as failed, not silently empty.
- No emoji, no exclamation marks, no "unlock", "dream", "supercharge".

## 8. Accessibility

- Contrast: body text at least 7:1 on paper in both themes; accent at least 4.5:1.
- Every chart has a text equivalent (a table or a sentence with the numbers).
- Focus ring: 2px accent outline, offset 2px.
- Respects `prefers-color-scheme` and `prefers-reduced-motion` (there is no motion anyway).

## 9. README art

One banner in light and dark: the wordmark set in ET Book with a single accent rule and a mono strip of the latest sweep figures. No illustration. Three to five badges, flat style, ink label and accent value.
