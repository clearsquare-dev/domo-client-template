# Domo Prospect Demo Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **No git repo here.** Neither `~/.claude/skills` nor the `clearsquare` project directory is a git repository, so steps that would normally end in `git commit` are replaced with a manual verification step instead. Do not run `git init` unless the user asks for it.

**Goal:** Build a new Claude Code skill, `domo-prospect-demo`, that scrapes a prospect's website, asks how many KPIs to show, and generates + publishes a themed Domo pro-code demo dashboard (synthetic data, ApexCharts) to the Clearsquare Domo instance, returning the app link.

**Architecture:** A deterministic Python scraper (`scripts/scrape_site.py`, requests + BeautifulSoup) does mechanical extraction (colors, fonts, logo, text) and hands back structured JSON. A `SKILL.md` documents the orchestration workflow — Claude reads the JSON, reasons about industry/palette/KPI content (this part is not scriptable, it needs per-prospect judgment), then scaffolds a Domo custom app using the existing `domo-apps` skill's conventions (`domo init` / manifest / `domo publish`), with a confirmation gate before the actual publish.

**Tech Stack:** Python 3 (`requests`, `beautifulsoup4` — already present in `clearsquare/.venv` and assumed available via system `python3` elsewhere, matching the precedent in `fieldroutes-customer-report/scripts/`), Domo CLI (`ryuu`, already installed at `/opt/homebrew/bin/domo`, v5.0.4), Tailwind CDN, ApexCharts CDN (per user's explicit request — not Chart.js).

---

## File Structure

- `~/.claude/skills/domo-prospect-demo/SKILL.md` — orchestration workflow + embedded templates (index.html/app.css/app.js/manifest.json)
- `~/.claude/skills/domo-prospect-demo/scripts/scrape_site.py` — HTML fetch + structured extraction, CLI entrypoint
- `~/.claude/skills/domo-prospect-demo/scripts/test_scrape_site.py` — unit tests (stdlib `unittest`, no live network)
- `clearsquare/apps/<company-slug>-demo/` — one generated Domo app per prospect (created at runtime, not part of this plan except for the Task 6 verification app)

---

### Task 1: Scraper — title/description + color extraction (TDD)

**Files:**
- Create: `~/.claude/skills/domo-prospect-demo/scripts/scrape_site.py`
- Create: `~/.claude/skills/domo-prospect-demo/scripts/test_scrape_site.py`

- [ ] **Step 1: Write the failing tests**

```python
# ~/.claude/skills/domo-prospect-demo/scripts/test_scrape_site.py
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

import scrape_site as ss


SAMPLE_HTML = """
<html>
<head>
  <title>Acme Rocket Co - Fly Higher</title>
  <meta name="description" content="Acme builds rockets for small business.">
  <meta name="theme-color" content="#1B4F72">
  <link rel="icon" href="/favicon.ico">
  <style>
    body { font-family: 'Poppins', sans-serif; }
    .hero { background: #1B4F72; color: #FFFFFF; }
    .cta { background-color: #F39C12; }
  </style>
</head>
<body>
  <img src="/assets/acme-logo.svg" alt="Acme Rocket Co logo" class="site-logo">
  <h1>We build rockets</h1>
  <p>Acme Rocket Co helps small businesses launch payloads into orbit affordably.</p>
</body>
</html>
"""


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.soup = BeautifulSoup(SAMPLE_HTML, "html.parser")

    def test_extract_title_and_description(self):
        title, description = ss.extract_title_and_description(self.soup)
        self.assertEqual(title, "Acme Rocket Co - Fly Higher")
        self.assertEqual(description, "Acme builds rockets for small business.")

    def test_extract_colors_ranks_theme_color_first(self):
        colors, theme_color = ss.extract_colors(self.soup, SAMPLE_HTML)
        self.assertEqual(theme_color, "#1B4F72")
        self.assertEqual(colors[0], "#1b4f72")
        self.assertIn("#f39c12", colors)

    def test_extract_colors_excludes_neutrals(self):
        colors, _ = ss.extract_colors(self.soup, SAMPLE_HTML)
        self.assertNotIn("#ffffff", colors)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/.claude/skills/domo-prospect-demo/scripts && python3 -m unittest test_scrape_site.py -v`
Expected: `ModuleNotFoundError: No module named 'scrape_site'` (file doesn't exist yet)

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Scrape a homepage for brand colors, fonts, logo, and text context."""
import argparse
import json
import re
import sys
from collections import Counter
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
HEX_COLOR_RE = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")
NEUTRAL_HEXES = {
    "#fff", "#ffffff", "#000", "#000000", "#fafafa", "#f5f5f5", "#f8f8f8",
    "#eee", "#eeeeee", "#ccc", "#cccccc", "#ddd", "#dddddd",
}


def fetch_html(url, timeout=10):
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_title_and_description(soup):
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    description = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        description = meta["content"].strip()
    return title, description


def extract_colors(soup, html):
    candidates = Counter()

    theme_meta = soup.find("meta", attrs={"name": "theme-color"})
    theme_color = theme_meta["content"].strip() if theme_meta and theme_meta.get("content") else None

    style_text = " ".join(tag.get_text() for tag in soup.find_all("style"))
    inline_styles = " ".join(tag.get("style", "") for tag in soup.find_all(style=True))
    combined = style_text + " " + inline_styles

    for match in HEX_COLOR_RE.findall(combined):
        normalized = match.lower()
        if normalized not in NEUTRAL_HEXES:
            candidates[normalized] += 1

    ranked = [color for color, _ in candidates.most_common(8)]
    if theme_color and theme_color.lower() not in ranked:
        ranked.insert(0, theme_color.lower())

    return ranked, theme_color


if __name__ == "__main__":
    pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/.claude/skills/domo-prospect-demo/scripts && python3 -m unittest test_scrape_site.py -v`
Expected: `Ran 3 tests ... OK`

- [ ] **Step 5: Verify (no git — manual check)**

Confirm `scrape_site.py` and `test_scrape_site.py` exist and the 3 tests above pass. No commit needed (no repo).

---

### Task 2: Scraper — font and logo extraction (TDD)

**Files:**
- Modify: `~/.claude/skills/domo-prospect-demo/scripts/scrape_site.py`
- Modify: `~/.claude/skills/domo-prospect-demo/scripts/test_scrape_site.py`

- [ ] **Step 1: Add the failing tests**

Add to `test_scrape_site.py`, inside `ExtractionTests`:

```python
    def test_extract_fonts(self):
        fonts = ss.extract_fonts(self.soup)
        self.assertIn("Poppins", fonts)

    def test_extract_logo_resolves_relative_url(self):
        logo = ss.extract_logo(self.soup, "https://acme.example.com/")
        self.assertEqual(logo, "https://acme.example.com/assets/acme-logo.svg")

    def test_extract_logo_falls_back_to_og_image(self):
        html = (
            "<html><head><meta property='og:image' content='/social/share.png'>"
            "</head><body><img src='/banner.png'></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        logo = ss.extract_logo(soup, "https://acme.example.com/")
        self.assertEqual(logo, "https://acme.example.com/social/share.png")

    def test_extract_logo_falls_back_to_favicon(self):
        html = (
            "<html><head><link rel='icon' href='/fav.ico'></head>"
            "<body><img src='/banner.png'></body></html>"
        )
        soup = BeautifulSoup(html, "html.parser")
        logo = ss.extract_logo(soup, "https://acme.example.com/")
        self.assertEqual(logo, "https://acme.example.com/fav.ico")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/.claude/skills/domo-prospect-demo/scripts && python3 -m unittest test_scrape_site.py -v`
Expected: `AttributeError: module 'scrape_site' has no attribute 'extract_fonts'`

- [ ] **Step 3: Implement `extract_fonts` and `extract_logo`**

Add to `scrape_site.py`, after `extract_colors`:

```python
def extract_fonts(soup):
    fonts = []
    for link in soup.find_all("link", href=True):
        href = link["href"]
        if "fonts.googleapis.com" in href or "fonts.google.com" in href:
            fonts.append(href)

    style_text = " ".join(tag.get_text() for tag in soup.find_all("style"))
    for match in re.findall(r"font-family:\s*([^;{}]+)", style_text):
        name = match.split(",")[0].strip().strip("'\"")
        if name and name.lower() not in ("inherit", "sans-serif", "serif", "monospace"):
            fonts.append(name)

    seen = []
    for f in fonts:
        if f not in seen:
            seen.append(f)
    return seen[:5]


def extract_logo(soup, base_url):
    for img in soup.find_all("img"):
        class_attr = img.get("class") or []
        haystack = " ".join([
            img.get("alt", ""),
            " ".join(class_attr),
            img.get("id", ""),
            img.get("src", ""),
        ]).lower()
        if "logo" in haystack and img.get("src"):
            return urljoin(base_url, img["src"])

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        return urljoin(base_url, og_image["content"])

    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)
        if "icon" in rel_str.lower() and link.get("href"):
            return urljoin(base_url, link["href"])

    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/.claude/skills/domo-prospect-demo/scripts && python3 -m unittest test_scrape_site.py -v`
Expected: `Ran 7 tests ... OK`

- [ ] **Step 5: Verify (no git — manual check)**

Confirm all 7 tests pass.

---

### Task 3: Scraper — body text, `scrape()` orchestrator, CLI entrypoint (TDD)

**Files:**
- Modify: `~/.claude/skills/domo-prospect-demo/scripts/scrape_site.py`
- Modify: `~/.claude/skills/domo-prospect-demo/scripts/test_scrape_site.py`

- [ ] **Step 1: Add the failing tests**

Add to `test_scrape_site.py`, inside `ExtractionTests`:

```python
    def test_extract_body_text_strips_scripts_and_truncates(self):
        html = "<html><body><script>var x=1;</script><p>" + ("hello " * 1000) + "</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        text = ss.extract_body_text(soup, max_chars=50)
        self.assertNotIn("var x=1", text)
        self.assertLessEqual(len(text), 50)
```

Add a new test class at the bottom of the same file, above `if __name__ == "__main__":`:

```python
class ScrapeIntegrationTests(unittest.TestCase):
    @patch("scrape_site.fetch_html")
    def test_scrape_success(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_HTML
        result = ss.scrape("https://acme.example.com/")
        self.assertTrue(result["scrape_ok"])
        self.assertEqual(result["title"], "Acme Rocket Co - Fly Higher")
        self.assertEqual(result["logo_url"], "https://acme.example.com/assets/acme-logo.svg")

    @patch("scrape_site.fetch_html")
    def test_scrape_handles_fetch_failure(self, mock_fetch):
        mock_fetch.side_effect = requests.ConnectionError("boom")
        result = ss.scrape("https://doesnotexist.example.com/")
        self.assertFalse(result["scrape_ok"])
        self.assertIn("boom", result["error"])
```

Add `import requests` near the top of `test_scrape_site.py` (alongside the existing imports) since this test class references `requests.ConnectionError` directly.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd ~/.claude/skills/domo-prospect-demo/scripts && python3 -m unittest test_scrape_site.py -v`
Expected: `AttributeError: module 'scrape_site' has no attribute 'extract_body_text'`

- [ ] **Step 3: Implement `extract_body_text`, `scrape`, and `main`**

Add to `scrape_site.py`, after `extract_logo`, replacing the placeholder `if __name__ == "__main__": pass` block at the end:

```python
def extract_body_text(soup, max_chars=3000):
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]


def scrape(url):
    result = {
        "url": url,
        "scrape_ok": False,
        "title": "",
        "meta_description": "",
        "theme_color": None,
        "colors": [],
        "fonts": [],
        "logo_url": None,
        "body_text": "",
        "error": None,
    }
    try:
        html = fetch_html(url)
    except requests.RequestException as exc:
        result["error"] = str(exc)
        return result

    soup = BeautifulSoup(html, "html.parser")
    title, description = extract_title_and_description(soup)
    colors, theme_color = extract_colors(soup, html)

    result.update({
        "scrape_ok": True,
        "title": title,
        "meta_description": description,
        "theme_color": theme_color,
        "colors": colors,
        "fonts": extract_fonts(soup),
        "logo_url": extract_logo(soup, url),
        "body_text": extract_body_text(soup),
    })
    return result


def main():
    parser = argparse.ArgumentParser(description="Scrape a homepage for brand style + context.")
    parser.add_argument("url", help="Homepage URL to scrape")
    args = parser.parse_args()
    print(json.dumps(scrape(args.url), indent=2))


if __name__ == "__main__":
    main()
```

Remove the old `if __name__ == "__main__": pass` stub left over from Task 1.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ~/.claude/skills/domo-prospect-demo/scripts && python3 -m unittest test_scrape_site.py -v`
Expected: `Ran 10 tests ... OK`

- [ ] **Step 5: Verify (no git — manual check)**

Confirm all 10 tests pass and `scrape_site.py` has no leftover stub code.

---

### Task 4: Real-world smoke test of the scraper

**Files:** none (verification only)

- [ ] **Step 1: Run the scraper against a real site**

Run: `python3 ~/.claude/skills/domo-prospect-demo/scripts/scrape_site.py "https://clearsquare.co"`

- [ ] **Step 2: Inspect the output**

Confirm: `scrape_ok` is `true`; `title` and `colors` are non-empty and look plausible; `logo_url` (if present) resolves to a real, absolute image URL. If `scrape_ok` is `false` or the extraction looks off (e.g. only neutral colors found), note it — this is expected to happen on some real sites (JS-rendered pages, bot-blocking) and confirms the fallback path in Step 1 of the SKILL.md workflow (Task 5) is necessary, not just theoretical.

- [ ] **Step 3: Try a second, different site**

Run the same command against one more real company site of your choice (something with a distinct brand color, e.g. a site with a strong red/orange/green scheme) to confirm color ranking isn't a fluke of the first site's palette.

**Addendum (discovered during execution):** the first real-world run against
clearsquare.co and stripe.com came back with empty `colors`/`fonts` because
both sites (like most modern marketing sites) load their real CSS via linked
stylesheets, not inline `<style>` tags. User approved extending the scraper to
also fetch and scan linked `<link rel="stylesheet">` files
(`extract_stylesheet_urls` + `fetch_linked_stylesheets`, wired into `scrape()`
via a new `extra_css` parameter on `extract_colors`/`extract_fonts`). A second
pass then showed the ranked color list dominated by generic UI grays
(`#999`, `#333`, `#e6e6e6`, ...); replaced the exact-match `NEUTRAL_HEXES` set
with a grayscale-distance heuristic (`_is_neutral_color`), and cleaned up font
extraction to drop `!important` suffixes, generic CSS keywords, and icon-font
names. All of this is additive to `scrape_site.py`'s existing functions — the
`scrape()` JSON output shape (documented in Task 5's SKILL.md) is unchanged.

---

### Task 5: Write SKILL.md

**Files:**
- Create: `~/.claude/skills/domo-prospect-demo/SKILL.md`

- [ ] **Step 1: Write the full skill file**

```markdown
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
python3 ~/.claude/skills/domo-prospect-demo/scripts/scrape_site.py "<homepage-url>"
```

Returns JSON: `scrape_ok`, `title`, `meta_description`, `theme_color`, `colors`
(ranked hex list, most-referenced first), `fonts`, `logo_url` (absolute URL or
`null`), `body_text` (truncated visible text), `error`.

If `scrape_ok` is `false`, tell the user the scrape failed and continue with the
neutral fallback palette below rather than aborting:

- primary `#0F172A`, secondary `#334155`, accent `#2563EB`, no logo.

### 2. Infer context

No script for this step — reason over the JSON yourself:

- **Company display name**: from `title`, stripped of boilerplate suffixes like
  `" | Home"` or `" - Official Site"`.
- **One-line description / industry vertical**: from `meta_description` +
  `body_text`. This drives what the KPIs and chart topics will be about.
- **Final 3-color palette** (primary/secondary/accent): pick from `colors`,
  preferring `theme_color` as primary if present. Fall back to the neutral
  palette above if fewer than 3 usable colors were extracted. Avoid low-contrast
  pairings (e.g. two near-identical blues) — if in doubt, check the `dataviz`
  skill's color guidance.

### 3. Ask how many KPIs

Use `AskUserQuestion`:

- question: "How many KPI tiles should the demo dashboard have?"
- header: "KPI count"
- options: `3` ("Minimal, punchy"), `4` ("Standard dashboard row"), `6` ("Two
  rows of 3"), `8` ("Dense, data-heavy")

(The user can type any other number via the built-in "Other" option.)

### 4. Generate synthetic content

For the chosen KPI count plus **one trend chart** and **one breakdown chart**,
all thematically tied to the inferred industry — e.g. a field-service company
gets "Active Work Orders" / "Technician Utilization"; a SaaS company gets "MRR"
/ "Net Revenue Retention". Every value is fabricated. Never imply it's real
client data — the header always says "Demo Dashboard".

### 5. Scaffold the app

```bash
cd apps && domo init -n "<company-slug>-demo" -t "hello world" --no-datasets
```

Then overwrite the four generated files using the templates below, substituting
your generated content in place of the `<PLACEHOLDER>` markers.

### 6. Confirm before publishing

Use `AskUserQuestion`:

- question: "Ready to publish '<Company> Demo Dashboard' to the Clearsquare
  Domo instance? KPIs: <list>. Charts: <trend title>, <breakdown title>.
  Palette: <hex, hex, hex>. Logo: <logo_url or 'none'>."
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

### manifest.json

```json
{
  "name": "<company-slug>-demo",
  "version": "1.0.0",
  "fullpage": true,
  "size": { "width": 6, "height": 4 },
  "datasetsMapping": []
}
```

### index.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title><COMPANY_NAME> Demo Dashboard</title>

  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.domo.com/domo.js/1/domo.js"></script>
  <script
    src="https://unpkg.com/ryuu.js@4.6.0/dist/domo.js"
    integrity="sha384-YYsd9wQ+wDlUWhvpfGdptxmNYIqBC+52oJtWgPKJadbs3sSFTY/+ZotPbEHTTRWz"
    crossorigin="anonymous">
  </script>
  <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>

  <link rel="stylesheet" href="app.css" />
</head>
<body>
  <div id="loading" class="flex items-center justify-center h-screen text-lg">Loading...</div>
  <div id="error" style="display:none" class="p-8 text-red-600"></div>

  <div id="app" style="display:none" class="p-8">
    <header class="flex items-center gap-4 mb-8">
      <img id="brand-logo" src="" alt="" class="h-10" style="display:none" />
      <div>
        <h1 id="brand-title" class="text-2xl font-bold"></h1>
        <p id="brand-subtitle" class="text-sm" style="color: var(--text-secondary)"></p>
      </div>
    </header>

    <div id="kpi-grid" class="kpi-grid mb-8"></div>

    <div class="table-grid">
      <div class="chart-card">
        <h2 class="chart-title" id="trend-chart-title"></h2>
        <div id="trend-chart"></div>
      </div>
      <div class="chart-card">
        <h2 class="chart-title" id="breakdown-chart-title"></h2>
        <div id="breakdown-chart"></div>
      </div>
    </div>
  </div>

  <script src="app.js"></script>
</body>
</html>
```

### app.css

```css
:root {
  --primary: <PRIMARY_HEX>;
  --secondary: <SECONDARY_HEX>;
  --accent: <ACCENT_HEX>;
  --card-bg: #ffffff;
  --border: #e5e7eb;
  --text-secondary: #6b7280;
}

.kpi-grid { display: grid; grid-template-columns: repeat(<KPI_COLUMNS>, 1fr); gap: 1rem; }

.kpi-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-top: 3px solid var(--primary);
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem;
}

.kpi-label { font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-value { font-size: 1.75rem; font-weight: 700; color: #111827; }
.kpi-delta-up { color: #059669; font-size: 0.85rem; }
.kpi-delta-down { color: #dc2626; font-size: 0.85rem; }

.table-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }

.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem;
}

.chart-title { font-size: 1rem; font-weight: 600; margin-bottom: 0.75rem; color: #111827; }
```

Pick `KPI_COLUMNS` as: 3 if KPI count ≤ 3, else 4 if count ≤ 8, else 5.

### app.js

```js
const BRAND = {
  name: "<COMPANY_NAME>",
  subtitle: "<ONE_LINE_DESCRIPTION>",
  logoUrl: <LOGO_URL_OR_null>,
};

const PALETTE = { primary: "<PRIMARY_HEX>", secondary: "<SECONDARY_HEX>", accent: "<ACCENT_HEX>" };

const KPIS = [
  // one object per KPI, e.g.:
  // { label: "Active Work Orders", value: "1,284", deltaPct: 12.4 },
];

const TREND_CHART = {
  title: "<TREND_CHART_TITLE>",
  categories: [/* e.g. "Jan","Feb",... 12 points */],
  series: [{ name: "<SERIES_NAME>", data: [/* 12 numbers */] }],
};

const BREAKDOWN_CHART = {
  title: "<BREAKDOWN_CHART_TITLE>",
  labels: [/* 3-5 category names */],
  series: [/* matching numbers */],
};

function renderBrand() {
  document.getElementById('brand-title').textContent = BRAND.name + ' — Demo Dashboard';
  document.getElementById('brand-subtitle').textContent = BRAND.subtitle;
  if (BRAND.logoUrl) {
    const logo = document.getElementById('brand-logo');
    logo.src = BRAND.logoUrl;
    logo.alt = BRAND.name + ' logo';
    logo.style.display = 'block';
  }
}

function renderKpis() {
  const grid = document.getElementById('kpi-grid');
  grid.innerHTML = KPIS.map(kpi => `
    <div class="kpi-card">
      <div class="kpi-label">${kpi.label}</div>
      <div class="kpi-value">${kpi.value}</div>
      <div class="${kpi.deltaPct >= 0 ? 'kpi-delta-up' : 'kpi-delta-down'}">
        ${kpi.deltaPct >= 0 ? '▲' : '▼'} ${Math.abs(kpi.deltaPct)}%
      </div>
    </div>
  `).join('');
}

function renderCharts() {
  document.getElementById('trend-chart-title').textContent = TREND_CHART.title;
  document.getElementById('breakdown-chart-title').textContent = BREAKDOWN_CHART.title;

  new ApexCharts(document.querySelector('#trend-chart'), {
    chart: { type: 'line', height: 300, toolbar: { show: false } },
    series: TREND_CHART.series,
    xaxis: { categories: TREND_CHART.categories },
    colors: [PALETTE.primary],
    stroke: { curve: 'smooth', width: 3 },
  }).render();

  new ApexCharts(document.querySelector('#breakdown-chart'), {
    chart: { type: 'donut', height: 300 },
    series: BREAKDOWN_CHART.series,
    labels: BREAKDOWN_CHART.labels,
    colors: [PALETTE.primary, PALETTE.secondary, PALETTE.accent],
  }).render();
}

function init() {
  try {
    renderBrand();
    renderKpis();
    renderCharts();
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
  } catch (err) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').textContent = 'Failed to render dashboard.';
    document.getElementById('error').style.display = 'block';
    console.error(err);
  }
}

init();
```

## Getting the published app link

<!-- FILLED IN BY TASK 6 — verified live against the Clearsquare instance -->

## Troubleshooting

- `ModuleNotFoundError: No module named 'requests'` → `pip3 install requests beautifulsoup4`
- Scrape returns `scrape_ok: false` → site may block scraping (403) or require JS
  rendering; proceed with the neutral fallback palette rather than aborting.
- `domo` is not defined in the browser console → missing the `domo.js`/`ryuu.js`
  CDN tags (see the `index.html` template above). See the `domo-apps` skill for
  more detail.
```

- [ ] **Step 2: Verify (no git — manual check)**

Read the file back and confirm the frontmatter parses (name/description present)
and every template code block is syntactically complete (matching braces/tags).

---

### Task 6: Live end-to-end verification

**Files:**
- Modify: `~/.claude/skills/domo-prospect-demo/SKILL.md` (fill in "Getting the
  published app link")
- Create (real, live): `clearsquare/apps/clearsquare-demo/`

This task actually runs the new skill once, against Clearsquare's own marketing
site (safe, permission-clear target, and it doubles as a dogfood test), to prove
the pipeline works end to end and to discover the real published-app URL format
— which cannot be guessed (see CLAUDE.md's rule against fabricating URLs; the
`domo` CLI's `publish`/`ls` output doesn't document a URL format up front).

- [ ] **Step 1: Scrape**

```bash
python3 ~/.claude/skills/domo-prospect-demo/scripts/scrape_site.py "https://clearsquare.co"
```

Read the output. Note `title`, `colors`, `logo_url`.

- [ ] **Step 2: Infer content**

Pick a 3-color palette from the output (or the neutral fallback if extraction
came back thin). Write down: company name, one-line description, 4 KPI
definitions (label/value/deltaPct) relevant to a Domo implementation partner
(e.g. "Active Client Dashboards", "Avg. Dataflow Runtime", "Data Freshness
SLA Hit Rate", "Open Support Tickets"), one trend chart (12 monthly points),
one breakdown chart (3-4 categories).

- [ ] **Step 3: Scaffold**

```bash
cd /Users/cristiancruz/PycharmProjects/clearsquare/apps && domo init -n "clearsquare-demo" -t "hello world" --no-datasets
```

- [ ] **Step 4: Fill in the four files**

Overwrite `apps/clearsquare-demo/manifest.json`, `index.html`, `app.css`,
`app.js` using the Task 5 templates, substituting the content from Step 2.

- [ ] **Step 5: Local preview**

```bash
cd /Users/cristiancruz/PycharmProjects/clearsquare/apps/clearsquare-demo && domo dev
```

Open the printed `localhost` URL in a browser. Confirm: logo (or text header if
none) renders, all 4 KPI tiles render with values, both ApexCharts charts
render with the chosen palette, no console errors. Stop the dev server
(Ctrl+C) when done.

- [ ] **Step 6: Confirm with the user before publishing**

Ask in chat (not just in the skill's own `AskUserQuestion` flow, since this is
you, the implementer, about to perform a real write against the Clearsquare
Domo instance per CLAUDE.md's pre-write briefing rule): summarize what's about
to be published (app name, KPIs, charts, palette, target folder) and wait for
explicit go-ahead.

- [ ] **Step 7: Publish**

```bash
cd /Users/cristiancruz/PycharmProjects/clearsquare/apps/clearsquare-demo && domo publish
```

Capture the full stdout/stderr.

- [ ] **Step 8: Determine the real app link**

```bash
domo ls
```

Find `clearsquare-demo` in the list and note its ID. Check whether `domo
publish`'s own output already printed a usable URL. If not, log into the
Clearsquare Domo instance in a browser (`https://$DOMO_INSTANCE`, credentials
already set up per CLAUDE.md) and locate the published app via Admin > Apps or
the App Studio / Asset Library, to find the actual browsable URL pattern for a
published custom app design.

- [ ] **Step 9: Document the real link pattern**

Edit `~/.claude/skills/domo-prospect-demo/SKILL.md`, replacing the
`<!-- FILLED IN BY TASK 6 -->` placeholder under "Getting the published app
link" with the actual confirmed command(s) and/or URL template (e.g. how to
turn a design `id` from `build/manifest.json` into the shareable link), based
on what Step 8 found — not a guess.

- [ ] **Step 10: Verify (no git — manual check)**

Confirm the SKILL.md placeholder is gone and replaced with real, verified
content. Re-read the full file once to check it's internally consistent (no
leftover TODOs, no ApexCharts/Chart.js mismatch, no stray template markers).

- [ ] **Step 11: Ask about cleanup**

Ask the user whether to keep the `clearsquare-demo` app live (useful as a
permanent internal example) or remove it now that the link format is
confirmed (`domo delete <id>`). Do not delete without an explicit answer.

---

## Self-Review

**Spec coverage:**
- Scrape homepage only, structured JSON output → Task 1-3 ✓
- Ask KPI count via AskUserQuestion → SKILL.md step 3 (Task 5) ✓
- Industry-informed KPI/chart content, no hardcoded industry table → SKILL.md
  step 4 (Task 5) ✓
- Synthetic data only, no Domo dataset → templates in Task 5, empty
  `datasetsMapping` ✓
- ApexCharts (not Chart.js) → app.js template, index.html CDN tag ✓
- Real logo hotlinked → `extract_logo` (Task 2) + `BRAND.logoUrl` (Task 5) ✓
- Palette extraction + neutral fallback → `extract_colors` (Task 1) + SKILL.md
  step 1/2 fallback (Task 5) ✓
- Pre-publish confirmation gate → SKILL.md step 6 (Task 5) ✓
- Return the link → SKILL.md step 8 + Task 6 (discovers and documents the real
  format) ✓
- Skill lives at `~/.claude/skills/` (user-level) → confirmed throughout ✓
- Generated apps under `clearsquare/apps/<slug>-demo/` per CLAUDE.md's project
  map → SKILL.md step 5, Task 6 ✓

**Placeholder scan:** the only intentional placeholder is the "Getting the
published app link" section in SKILL.md, which Task 6 fills in with real,
verified content by design (the actual URL genuinely cannot be known until a
real publish happens) — not a shortcut, an explicit two-step discovery
sequenced across Task 5 → Task 6.

**Type/name consistency:** `scrape()`'s return dict keys (`scrape_ok`, `title`,
`meta_description`, `theme_color`, `colors`, `fonts`, `logo_url`, `body_text`,
`error`) are used identically in SKILL.md's workflow description and in the
Task 3 tests. `PALETTE`/`BRAND`/`KPIS`/`TREND_CHART`/`BREAKDOWN_CHART` names in
the `app.js` template match between the template definition and the render
functions that consume them.

---

## Execution Handoff

Plan complete and saved to `~/.claude/skills/domo-prospect-demo/PLAN.md` (not
`docs/superpowers/plans/...` — the `clearsquare` project isn't a git repo, and
this skill's real home is `~/.claude/skills/`, not the project). Two execution
options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task,
review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans,
batch execution with checkpoints

**Which approach?**
