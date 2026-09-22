---
name: domo-app-studio-build
description: >
  Build Domo dashboards from the API with out-of-the-box KPI cards: create or load a dataset, create an
  App Studio app and pages, create native cards (single values, bars, donuts, tables, selectors, beast
  modes), and arrange them on the page layout. Use whenever the user wants cards or a dashboard
  built programmatically, a demo/mock dataset stood up in Domo, or an App Studio page assembled —
  including "build me a dashboard for X", "create cards on this page", "upload this CSV as a dataset",
  or "lay these cards out". Not for pro-code apps (use domo-apps) or reading cards (use domo-card).
---

# Domo App Studio Build

Everything here was verified on the Clearsquare partner instance (Sep 2026) with a developer
token. Worked example: `manual/sales_churn_demo/` (README, data generator, `build_cards.py`,
`apply_layout.py`). Reusable helpers live in `scripts/` next to this file.

> **Write skill.** Every step below is a write. Give the CLAUDE.md pre-write briefing before the
> first call of each phase (dataset, app, cards, layout). Only touch objects you created in this
> session; other people's cards need explicit instruction.

## Workflow

1. **Design first** — decide the dataset grain and which columns each card needs. If the data must
   support retention/churn/cohort analysis with plain cards, precompute row-level attributes
   (status flags, first/last dates, cohort year, order type) rather than relying on beast modes.
2. **Dataset** — `scripts/create_dataset.py <csv> "<name>"` creates an API dataset from the CSV
   header (types inferred, override with `--types`) and loads the rows.
3. **App + page** — `scripts/domo_api.py` has `create_app()` / `rename_page()`.
4. **Cards** — build bodies with `scripts/cards_lib.py`, create with `PUT /api/content/v3/cards/kpi?pageId=`.
   Save card IDs to a JSON file keyed by a stable name; make the script idempotent (skip existing keys).
5. **Verify every card** — `POST /api/content/v1/cards/{id}/data` for rows, then read the definition
   back and check mappings against the rules below (the page renderer is stricter than the data API).
6. **Layout** — `scripts/apply_layout.py` positions cards and section headers on the 60-column grid.
7. **Hand-off** — URL is `https://{instance}/app-studio/{appId}/pages/{pageId}`. Write a README in
   `manual/<project>/` with dataset ID, app/page IDs, card map, and anything you learned.

## Auth

Same pattern as every other skill: load `.env`, use `X-DOMO-Developer-Token`. `scripts/domo_api.py`
wraps it (`req(method, path, body=None, raw=None, ctype=...)` returns `(status, text)`).

## Endpoints

| Task | Call | Notes |
| :-- | :-- | :-- |
| Create dataset | `POST /api/data/v2/datasources` | body `{"dataSourceName","description","dataProviderType":"api","schema":{"columns":[{name,type}]}}`. Field is `dataSourceName` (not `name`). v3 POST is 405. Returns `dataSource.dataSourceId`. |
| Load rows | `POST /api/data/v3/datasources/{id}/uploads` `{"action":"REPLACE"}` → `PUT …/uploads/{uploadId}/parts/{n}` (text/csv, **no header row**) → `PUT …/uploads/{uploadId}/commit` `{"index":true,"action":"REPLACE"}` | Split big files into a few parts. Commit returns row/column counts. |
| Query check | `POST /api/query/v1/execute/{id}` `{"sql":"SELECT COUNT(*) FROM table"}` | Confirms types and row count. |
| Create app | `POST /api/content/v1/dataapps` `{"title","description"}` | Returns `dataAppId` and `landingViewId` (= first page ID). |
| Rename page | `PUT /api/content/v1/pages/{pageId}` `{"pageId","title","pageName"}` | |
| Whole app | `GET/PUT /api/content/v1/dataapps/{id}?includeHiddenViews=true` | Round-trip to set `views[].visible`, theme, nav. |
| Read card def | `PUT /api/content/v3/cards/kpi/definition` `{"urn":"<cardId>"}` | Ground truth for any card shape — read a UI-built card of the same chart type before inventing one. |
| Create card | `PUT /api/content/v3/cards/kpi?pageId={pageId}` | POST is 405. Generic `400 Bad Request` = body-shape problem. |
| Update card | `PUT /api/content/v3/cards/kpi/{cardId}` | Full definition replacement, same body as create. |
| Delete card | `DELETE /api/content/v1/cards/{cardId}` | |
| Card rows | `POST /api/content/v1/cards/{cardId}/data` `{}` | Rendered rows; passes even when the page won't draw the card. |
| Card image | `PUT /api/content/v1/cards/kpi/{cardId}/render?parts=image` `{"scale":1,"height":420,"width":640,"chartState":{"overrides":{}}}` | Base64 PNG of charts (tables always come back blank). Good for spotting "No data in filtered range" and legend/format problems. |
| Read layout | `GET /api/content/v4/pages/{pageId}/layouts` | Cards created with `pageId` appear in `content[]` as appendix entries. |
| Save layout | `PUT /api/content/v4/pages/layouts/{layoutId}/writelock` → `PUT /api/content/v4/pages/layouts/{layoutId}` → `DELETE …/writelock` | Without the lock: `403 WL003`. |

## Card body (create and update)

```json
{
  "definition": {
    "subscriptions": {
      "big_number": {"name":"big_number","dataSourceId":"<ds>","columns":[<one aggregated column>],"filters":[],"orderBy":[],"groupBy":[],"fiscal":false,"projection":false,"distinct":false,"limit":1},
      "main": {"name":"main","dataSourceId":"<ds>","columns":[...],"filters":[],"orderBy":[],"groupBy":[...],
               "dateGrain":{"column":"<date col>"},"fiscal":false,"projection":false,"distinct":false}
    },
    "formulas": {"dsUpdated":[],"dsDeleted":[],"card":[<card-level beast modes>]},
    "annotations": {"new":[],"modified":[],"deleted":[]},
    "conditionalFormats": {"card":[],"datasource":[]},
    "controls": [],
    "segments": {"active":[],"create":[],"update":[],"delete":[]},
    "charts": {"main":{"component":"main","chartType":"badge_vert_bar","overrides":{},"goal":null}},
    "dynamicTitle": {"text":[{"text":"Title","type":"TEXT"}]},
    "dynamicDescription": {"text":[],"displayOnCardDetails":true},
    "chartVersion":"12","inputTable":false,"noDateRange":false,"title":"Title","description":""
  },
  "dataProvider": {"dataSourceId":"<ds>"},
  "variables": true,
  "columns": false
}
```

`scripts/cards_lib.py` builds this: `card(title, chart_type, columns, filters=, orderBy=, dateRange=,
monthGrain=, overrides=, formulas=, description=, limit=)` plus `col()`, `bcol()`, `cdist()`,
`month_item()`, `flt()`, `this_year()`, `last_months(n)`, `bm()`.

### Column mapping rules — the page renderer enforces these, the API does not

| Card | Columns | groupBy |
| :-- | :-- | :-- |
| Single value | one aggregated `VALUE` | `[]` |
| Bar / line / donut, one measure | dimension `ITEM`, measure `VALUE`, optional dimension `SERIES` | every non-aggregated column |
| Bar / line, two or more measures | dimension `ITEM`, **every measure `SERIES`** with its aggregation, no `VALUE` | the dimension |
| Table | **every column `VALUE`** (text columns without aggregation, measures with) | every non-aggregated column |
| Dropdown / checkbox selector | the column as `ITEM`; big_number = `COUNT` of that column | the column |

Getting this wrong gives a card whose `/data` call returns rows but the page shows blank or
"No data in filtered range". When unsure, read a UI-built card of the same type with the
definition endpoint and copy its mappings.

### Other rules

- `big_number.columns` must hold exactly one aggregated column for every chart type (the create
  API rejects an empty one). Hide it on the page with `hideSummary` in the layout if unwanted.
- Count distinct: `{"column":"X","aggregation":"COUNT","distinct":true}`. `COUNT_DISTINCT` → 400.
- Month buckets: column `{"column":"CalendarMonth","calendar":true,"mapping":"ITEM"}` with
  `main.dateGrain = {"column":"<date>","dateTimeElement":"MONTH"}`; groupBy `{"column":"CalendarMonth","calendar":true}`.
- Date ranges: `main.dateRangeFilter = {"column":{"column":"<date>","exprType":"COLUMN"},"dateTimeRange":{...}}`
  with `{"dateTimeRangeType":"INTERVAL_OFFSET","interval":"YEAR","offset":0,"count":0}` (this year) or
  `{"dateTimeRangeType":"ROLLING_PERIOD","interval":"MONTH","offset":0,"count":24}` (last 24 months).
- Year-as-number columns (LONG) used as ITEM/SERIES render as `$2,023` under a currency chart — add
  `"format":{"type":"number","format":"0","commas":false,"precision":0}` to that column. Multi-measure
  charts also want `overrides.never_use_time_scale = "true"`.
- Formats: currency `{"type":"currency","format":"###,###","commas":true,"percentMultiplied":true,"precision":0,"currency":"$"}`;
  abbreviated `{"type":"abbreviated","format":"$0.0"}`; percent `{"type":"percent","format":"###,###.0%","commas":true,"percentMultiplied":true,"precision":1,"percent":true}`.
- Override values are strings, even booleans and numbers. Useful: `lrg_legend_position` (Top/Hide),
  `label_format_y` (Currency/Number/Percentage), `currency_sym_position`, `never_use_time_scale`.
- `badge_line` fails on create; use `badge_two_trendline`/`badge_vert_bar`. Working types used so far:
  `badge_singlevalue`, `badge_vert_bar`, `badge_vert_stackedbar`, `badge_horiz_stackedbar`,
  `badge_vert_multibar`, `badge_donut`, `badge_basic_table`, `badge_dropdown_selector`.

### Card-level beast modes

Put each formula in `definition.formulas.card[]` and reference it from a column with
`{"formulaId":"<id>","mapping":"VALUE","alias":"...","format":{...}}` (no `aggregation`). `orderBy`
accepts `{"formulaId":"<id>","order":"DESCENDING"}`.

```json
{"id":"calculation_<uuid>","name":"YoY Change %","formula":"(<cy>) / NULLIF(<py>, 0)","query":"<same>",
 "status":"VALID","dataType":"DOUBLE","persistedOnDataSource":false,"initialPersistedOnDataSource":false,
 "isAggregatable":false,"bignumber":false,"nonAggregatedColumns":[],"nonAggregatedExpressions":[],
 "variable":false,"isCalculation":true,"saved":false,"cacheWindow":"non_dynamic","containsAggregation":true,
 "containsAnalytic":false,"invalidColumns":[],"formulaTemplateDependencies":[],"formulaDependencies":[],
 "columnPositions":[],"isControlled":false}
```

- Do **not** include `templateId`, `legacyId` or `formulaId` on the formula object: two formulas
  sharing `templateId:-1` are rejected with a generic 400. Domo assigns template IDs on save.
- `CASE … THEN NULL` → 500. Use `NULLIF(x, 0)`.
- Same-period YoY pattern:
  `SUM(CASE WHEN YEAR(\`d\`) = YEAR(CURRENT_DATE()) THEN \`v\` ELSE 0 END)` vs
  `SUM(CASE WHEN YEAR(\`d\`) = YEAR(CURRENT_DATE()) - 1 AND \`d\` <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 YEAR) THEN \`v\` ELSE 0 END)`.
- Dataset-level (shared) beast modes: `POST /api/query/v1/functions/template?strict=false` (see the
  community skill linked below), then reference by `formulaId` in `formulas.dsUpdated`.

## Layout

`pageLayoutV4` = `content[]` (one entry per card/header with display flags) + `standard.template[]`
(x/y/width/height on a 60-wide grid) + `compact.template[]` (12-wide, phone). `scripts/apply_layout.py`
takes a rows spec and does the rest, including the writelock dance. Conventions that read well:

- Filters row `h=6` with `hideTitle/hideBorder/hideMargins/fitToFrame` true.
- KPI tiles `h=12`, 5–6 across (`w=10` or `12`), summary visible (`hideSummary:false`).
- Section `HEADER` entries `h=4` (new entries need only `contentKey`, `type`, `text` and the flag set).
- Charts `h=20–22`, tables `h=22`, `hideSummary:true`.
- Anything not positioned goes to the appendix (`virtual`/`virtualAppendix` true).

## Verification checklist (do all of it before hand-off)

1. Every card: `/data` returns the expected row count and first row.
2. Every chart: read the definition back; mappings match the table above.
3. Charts: render the image; look at it (Read tool) — catches "No data in filtered range" and `$2,023`.
4. Tables: mappings all `VALUE`, groupBy covers the text columns (the image render can't check tables).
5. Layout: `GET /api/content/v3/stacks/{pageId}/cards?includeV4PageLayouts=true` — canvas entry count equals card count + headers.
6. The page's `views[].visible` is true and the app `enabled`.

## Known limits / open items

- App theme is left at the default; the theme lives in the app object (`GET/PUT /api/content/v1/dataapps/{id}`)
  with colour references, not hex strings.
- Period-over-period card types (`badge_pop_*`) were not exercised.
- Community reference with 200+ chart types and override keys:
  https://github.com/stahura/domo-ai-vibe-rules (`skills/app-studio/card-creation/references/`). It assumes
  `community-domo-cli`; the raw endpoints above are what that CLI calls. Its "empty big_number for
  singlevalue" advice is wrong on this instance.
