---
name: domo-prospect-demo
description: Scrape a prospective client's website, then build and publish a themed Domo pro-code demo dashboard with synthetic data to pitch back to them. Use when given a prospect's website URL and asked to build a sales demo, mockup, or POC dashboard in Domo for that company.
---

# Domo Prospect Demo Builder

Turns a prospect's website URL into a live, on-brand demo dashboard published as a
Domo pro-code app in the Clearsquare instance — for pitching back to that prospect.
Builds on the `domo-apps` skill for the scaffold/publish mechanics; see that skill
for anything not covered here (manifest details, troubleshooting `domo` CLI issues,
dataset querying patterns — not used by this skill since all data here is synthetic).

## Workflow

### 1. Scrape the site

```bash
python3 .claude/skills/domo-prospect-demo/scripts/scrape_site.py "<homepage-url>"
```

Returns JSON: `scrape_ok`, `title`, `meta_description`, `theme_color`, `colors`
(ranked hex list, most-referenced first — pulled from both inline styles and
linked stylesheets, with generic grays already filtered out), `fonts`,
`logo_url` (absolute URL or `null`), `body_text` (truncated visible text),
`error`.

If `scrape_ok` is `false`, tell the user the scrape failed and continue with the
neutral fallback palette below rather than aborting:

- primary `#0F172A`, secondary `#334155`, accent `#2563EB`, no logo.

If `scrape_ok` is `true` but `colors` came back empty (rare now that linked
stylesheets are scanned, but possible for JS-only sites or sites that block
scraping past the initial HTML), use the same fallback palette.

### 2. Infer context

No script for this step — reason over the JSON yourself:

- **Company display name**: from `title`, stripped of boilerplate suffixes like
  `" | Home"` or `" - Official Site"`.
- **One-line description / industry vertical**: from `meta_description` +
  `body_text`. This drives what the KPIs and chart topics will be about.
- **Final 3-color palette** (primary/secondary/accent): pick from `colors`,
  preferring `theme_color` as primary if present. Skip anything that still
  reads as a neutral/gray despite the script's filtering. Fall back to the
  neutral palette above if fewer than 3 usable colors were extracted. Avoid
  low-contrast pairings (e.g. two near-identical blues) — if in doubt, check
  the `dataviz` skill's color guidance.
- **Breakdown/filter dimension**: pick a segmentation that fits the industry
  and name exactly 3 categories under it — e.g. "Service Line" (Tax /
  Assurance / Advisory) for a CPA firm, "Region" (NA / EMEA / APAC) for a
  global company, "Business Unit" (Enterprise / Mid-Market / SMB) for a SaaS
  company. This dimension drives the breakdown donut, the second dashboard
  filter, and the per-category KPI variants generated in step 4.

### 3. Ask how many KPIs

Use `AskUserQuestion`:

- question: "How many KPI tiles should the demo dashboard have?"
- header: "KPI count"
- options: `3` ("Minimal, punchy"), `4` ("Standard dashboard row"), `6` ("Two
  rows of 3"), `8` ("Dense, data-heavy")

(The user can type any other number via the built-in "Other" option.)

### 4. Generate synthetic content

Every generated dashboard ships with a light/dark theme toggle and two live
filters (Period, and the categorical dimension from step 2) as standard
features — not something to ask the user about. That means the content you
generate must be richer than a single flat series:

- **KPIs** (the chosen count from step 3) thematically tied to the inferred
  industry — e.g. a field-service company gets "Active Work Orders" /
  "Technician Utilization"; a SaaS company gets "MRR" / "Net Revenue
  Retention".
- **One trend chart and one breakdown chart.** The breakdown chart always has
  exactly 3 categories (the dimension from step 2) — these double as the
  options for the second filter.
- **Monthly data split by category, not just a single flat total.** Build a
  12-point monthly array per category (`MONTHLY_BY_CATEGORY` in the template),
  each with a distinct, plausible shape — e.g. a tax-prep category spikes in
  Mar/Apr, a subscription category grows steadily. The "all categories" trend
  view and the breakdown totals are both derived from these by summing, so
  the two filters actually recompute the charts instead of just decorating
  the page.
- **Per-category KPI variants.** For every KPI, author a value + delta% +
  short (5-6 point) sparkline array for "all categories" AND for each of the 3
  categories individually (`KPI_DATA` in the template) — with plausible
  proportional differences, not the same number scaled uniformly. This is
  what makes the category filter feel real when a prospect clicks it.

Every value is fabricated. Never imply it's real client data — the header
always says "Demo Dashboard".

### 5. Scaffold the app

```bash
cd apps && domo init -n "<company-slug>-demo" -t "hello world" --no-datasets
```

Copy the four templates from `templates/` in this skill directory into the
scaffolded app directory, then edit each copy to replace the `<PLACEHOLDER>`
markers with your generated content (company name, palette, KPI/category
data, filter dimension, chart data) — see "Templates" below for what each
placeholder expects.

### 6. Confirm before publishing

Use `AskUserQuestion`:

- question: "Ready to publish '<Company> Demo Dashboard' to the Clearsquare
  Domo instance? KPIs: <list>. Charts: <trend title>, <breakdown title>.
  Filters: Period (3/6/12 months) + <category dimension> (<3 category
  names>). Theme: light/dark toggle included. Palette: <hex, hex, hex>.
  Logo: <logo_url or 'none'>."
- header: "Confirm publish"
- options: "Publish now" / "Let me review the files first"

If the user picks the second option, stop and let them inspect
`apps/<company-slug>-demo/` before being asked again.

### 7. Publish

```bash
cd apps/<company-slug>-demo && domo publish
```

### 8. Return the link

See "Getting the published app link" below.

## Templates

The four app files live in `templates/` in this skill directory (not inlined
here — they're large enough now to warrant standalone files):

- `templates/manifest.json` — one placeholder, `<COMPANY_SLUG>`.
- `templates/index.html` — static shell: theme-init script, logo/title header,
  theme toggle button, the two filter `<select>` elements, KPI grid, and two
  chart cards. Placeholders: `<COMPANY_NAME>`, `<COMPANY_SLUG>` (used in the
  localStorage theme key), `<CATEGORY_LABEL>` (the filter's visible label,
  e.g. "Service Line").
- `templates/app.css` — light/dark CSS variables (dark-mode surface/border/text
  colors are fixed neutrals, not brand-derived — only `--primary`,
  `--secondary`, `--accent` come from the scraped palette), KPI card
  sparkline/hover/entrance-animation styles, filter bar styling. Placeholders:
  `<PRIMARY_HEX>`, `<SECONDARY_HEX>`, `<ACCENT_HEX>`, `<KPI_COLUMNS>` (pick 3
  if KPI count ≤ 3, else 4 if count ≤ 8, else 5).
- `templates/app.js` — theme toggle logic, animated count-up KPI values,
  inline SVG sparklines, and the two filters (Period always fixed at
  3/6/12 months; the category filter driven by whatever 3 categories you
  pick). Placeholders are marked inline with comments showing the exact shape
  expected — `BRAND`, `PALETTE`, `ALL_CATEGORIES_LABEL`,
  `MONTHLY_BY_CATEGORY`, `KPI_META`, `KPI_DATA`, `BREAKDOWN_COLOR_BY_CATEGORY`,
  plus `<TREND_CHART_TITLE>`, `<TREND_SERIES_NAME>`, `<BREAKDOWN_CHART_TITLE>`.
  The render/update/animation functions below those constants are generic —
  don't rewrite them, only fill in the data blocks.

Copy each template into the scaffolded app directory as-is, then edit the
copies in place (don't edit the templates in the skill directory itself).

## Getting the published app link

`domo publish` always prints the link on success — no extra step needed:

```
Design can be found at https://<instance>/assetlibrary?designId=<id>
```

That's the URL to hand back to the user. Verified against the `ryuu` CLI's own
source (`linkToDomoWeb` in `publish.js`) and confirmed live: publishing
`clearsquare-demo` printed
`https://clearsquare-co-partner.domo.com/assetlibrary?designId=b71e85ac-2f22-46b6-94f1-457e5798ad06`,
matching this pattern exactly. `<id>` is also written to `manifest.json`'s
`id` field after publish, and `domo ls` shows the same link (in a slightly
different path form, `/assetlibrary/<id>/overview` — both resolve) for every
previously published design, if you need to look one up later without
re-publishing.

## Troubleshooting

- `ModuleNotFoundError: No module named 'requests'` → `pip3 install requests beautifulsoup4`
- Scrape returns `scrape_ok: false` → site may block scraping (403) or require JS
  rendering; proceed with the neutral fallback palette rather than aborting.
- Scrape succeeds but `colors`/`fonts` are empty → the site likely loads all its
  CSS from a stylesheet the scraper couldn't fetch (blocked, CORS-restricted
  host, or more than 5 linked stylesheets); fall back to the neutral palette.
- `domo` is not defined in the browser console → missing the `domo.js`/`ryuu.js`
  CDN tags (see the `templates/index.html` template). See the `domo-apps`
  skill for more detail.
- Dashboard loads but filters do nothing / charts don't update → the trend and
  breakdown ApexCharts instances (`trendChart`, `breakdownChart` module-level
  vars in `app.js`) must be created once in `renderCharts()` and updated in
  place via `.updateOptions()`/`.updateSeries()` on filter/theme change — don't
  destroy and recreate them per filter change, it causes flicker and loses the
  smooth transition.
- Trend line is unreadable in dark mode → this is why the trend chart's color
  is theme-aware (`accent` in dark mode, `primary` in light mode) rather than
  fixed; if a scraped `accent` color is itself too dark/desaturated to read on
  the dark background (`--bg: #0a0f1c`), pick a brighter accent in step 2
  rather than hardcoding a fixed chart color.
- KPI sparkline color looks wrong after a theme toggle → sparklines use the
  `.spark-up`/`.spark-down` CSS classes (which resolve `var(--up)`/`var(--down)`)
  rather than an inline `stroke` attribute, specifically so they follow the
  theme automatically. Don't switch that back to an inline hex stroke.
