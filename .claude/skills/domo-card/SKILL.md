---
name: domo-card
description: >
  Read and diagnose Domo cards — the charts and tables on a dashboard. Use this skill whenever the user
  mentions a card by name, ID, or Domo URL, wants to know what a card displays, which columns or beast
  modes it uses, which dataset feeds it, what its drill path or conditional formats are, or why a card is
  showing a wrong or unexpected number. Trigger even on casual references like "look at the retention
  card", "what feeds this card", "why is this KPI off", or when given a Domo card URL. Read-only.
---

# Domo Card

Inspect Domo cards via the **internal** API (`/api/content/v1/...`) using the project auth pattern.

> **Read-only skill.** Every call here is a GET, or a POST that only reads. Do not add write operations
> without an explicit request and the pre-write briefing CLAUDE.md requires.

> **Do not use the public Cards API** (`https://api.domo.com/v1/cards`). It requires OAuth2
> client-credentials, which this project does not have — it returns `401` with a developer token. See
> [Gotchas](#gotchas).

---

## Auth

Same pattern as `domo-query-dataset`, `domo-get-dataset-schema`, and `domo-dataflow`. Set `$AUTH_HEADER`
once and reuse it for every call in the same bash block.

```bash
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi

if [ -n "$DOMO_ACCESS_TOKEN" ]; then
  AUTH_HEADER="X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
else
  # Fallback: no DOMO_ACCESS_TOKEN set — legacy SID session (expires ~1hr, re-run on 401)
  LOCAL_CONFIG="./.domo_cli/configstore/ryuu/$DOMO_INSTANCE.json"
  REFRESH_TOKEN=$(python3 -c "import json; print(json.load(open('$LOCAL_CONFIG'))['refreshToken'])")
  ACCESS_TOKEN=$(curl -s -X POST "https://$DOMO_INSTANCE/api/oauth2/token" \
    -H "content-type: application/x-www-form-urlencoded" \
    -d "client_id=domo:internal:devstudio&grant_type=refresh_token&refresh_token=$REFRESH_TOKEN" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
  SID=$(curl -s "https://$DOMO_INSTANCE/api/oauth2/sid" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['sid'])")
  AUTH_HEADER="X-Domo-Authentication: $SID"
fi
```

## Inputs

| Given | Do this |
| :--- | :--- |
| Card ID (numeric, e.g. `684760974`) | Skip to [Recipe 2](#recipe-2-full-dump-fast-path) |
| Card name / partial title | [Recipe 1](#recipe-1-find-a-card-by-name) first |
| Domo URL `.../kpis/details/684760974` | The trailing number is the card ID |
| Page ID | [List cards on a page](#list-cards-on-a-page) |

---

## Recipe 1: Find a card by name

There is no working card-search endpoint under `/api/content`. Use global search with an entity filter.

```bash
curl -s -X POST "https://$DOMO_INSTANCE/api/search/v1/query" \
  -H "$AUTH_HEADER" -H "Content-Type: application/json" \
  -d '{"count":20,"offset":0,"query":"Retention Rate","filters":[],
       "entityList":[["card"]],"sort":{"isRelevance":true}}' \
 | python3 -c "
import json, sys
d = json.load(sys.stdin)
hits = d.get('searchObjects', [])
print(f\"{d.get('totalResultCount')} total, showing {len(hits)}\")
for h in hits:
    print(f\"  {h['databaseId']:>12} | {str(h.get('chartType')):24} | {str(h.get('ownedByName')):16} | {h.get('title')}\")
"
```

Card titles are in **`title`** — the `name` field is always `null`.

Each hit also carries `dataSourceIds`, `cardType`, `lastModified`, and `systemTags`, so you can filter
without a second call. To find every card built on a dataset:

```bash
  | python3 -c "
import json, sys
TARGET = '854b12df-76ed-4178-ae12-f18bd97f5291'
for h in json.load(sys.stdin).get('searchObjects', []):
    if TARGET in (h.get('dataSourceIds') or []):
        print(h['databaseId'], '|', h.get('title'))
"
```

---

## Recipe 2: Full dump (fast path)

Start here for any "what is this card / why is it wrong" question. Two calls, one digest.

```bash
CARD=684760974

curl -s "https://$DOMO_INSTANCE/api/content/v1/cards?urns=$CARD&parts=metadata,formulas,datasources,drillPath,conditionalFormats,slicers,owners,certification" \
  -H "$AUTH_HEADER" -o /tmp/card_meta.json

curl -s -X POST "https://$DOMO_INSTANCE/api/content/v1/cards/$CARD/data" \
  -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{}' -o /tmp/card_data.json

python3 - <<'EOF'
import json
c = json.load(open('/tmp/card_meta.json'))[0]
d = json.load(open('/tmp/card_data.json'))
dat = d.get('data') or {}

print(f"{c.get('title')}  [{c.get('urn')}]")
md = c.get('metadata') or {}
print(f"  chartType : {md.get('chartType')}   dateGrain: {md.get('defaultDateGrain')}")
print(f"  owner     : {c.get('ownerId')}   locked={c.get('locked')}  drillEnabled={c.get('allowTableDrill')}")

print("\n  SOURCES")
for ds in c.get('datasources') or []:
    print(f"    {ds['dataSourceId']}  {ds['dataSourceName']}  ({ds.get('dataType')})")

print("\n  DISPLAYED COLUMNS  (role | alias <- column)")
for col, ali, mp, m in zip(dat.get('columns',[]), dat.get('aliases',[]),
                           dat.get('mappings',[]), dat.get('metadata',[])):
    agg = ' agg' if m.get('aggregated') else ''
    print(f"    {mp:7} | {ali!r} <- {col}  ({m.get('type')}{agg})")

fm = c.get('formulas') or {}
fm = fm.get('formulas', fm) if isinstance(fm, dict) else fm
if fm:
    print("\n  CARD BEAST MODES")
    items = fm.items() if isinstance(fm, dict) else enumerate(fm)
    for k, f in items:
        if not isinstance(f, dict): continue
        print(f"    [{f.get('templateId','?')}] {f.get('name')}")
        print(f"        {' '.join(str(f.get('formula','')).split())[:220]}")

dp = c.get('drillPath')
if dp: print(f"\n  DRILL PATH: {json.dumps(dp)[:300]}")
cf = c.get('conditionalFormats')
if cf: print(f"  CONDITIONAL FORMATS: {json.dumps(cf)[:300]}")

print(f"\n  {dat.get('numRows')} rows x {dat.get('numColumns')} cols")
for r in (dat.get('rows') or [])[:5]:
    print('   ', r)
EOF
```

---

## Recipe 3: What does the card actually show?

`POST /api/content/v1/cards/{id}/data` with an empty body returns the card's **rendered** output — the
numbers a user sees, already aggregated and filtered. This is the closest equivalent to the public API's
"chart definition", and it is the ground truth for reconciling a suspect number.

```bash
curl -s -X POST "https://$DOMO_INSTANCE/api/content/v1/cards/$CARD/data" \
  -H "$AUTH_HEADER" -H "Content-Type: application/json" -d '{}' \
 | python3 -c "
import json, sys
dat = json.load(sys.stdin)['data']
for col, ali, mp in zip(dat['columns'], dat['aliases'], dat['mappings']):
    print(f'  {mp:7} | {ali!r} <- {col}')
print()
print(f\"{dat['numRows']} rows\")
for r in dat['rows'][:10]:
    print('  ', dict(zip(dat['aliases'], r)))
"
```

### `data` response fields

| Field | Meaning |
| :--- | :--- |
| `columns` | Underlying column names |
| `aliases` | Display labels shown on the card (**what the user sees**) |
| `mappings` | Axis role per column — see below |
| `metadata` | Per-column `type`, `aggregated`, `label`, `dataSourceId` |
| `formats` / `columnFormats` | Number, percent, and date formatting |
| `rows` | Rendered values; `rows[i][j]` ↔ `columns[j]` |
| `numRows`, `numColumns` | Counts |

### `mappings` vocabulary

| Value | Role |
| :--- | :--- |
| `ITEM` | X-axis / category |
| `VALUE` | Measure (Y-axis) |
| `SERIES` | Legend split / stacking dimension |

A table card reports every column as `VALUE`. A stacked bar reports `ITEM`, `VALUE`, `SERIES`.

> `aliases` frequently differ from `columns` — a card labelled `Report Date` may be built on
> `CalendarMonth`, and a beast mode's alias hides which underlying column it aggregates. Always reconcile
> both before concluding a card is wrong.

---

## Recipe 4: Beast modes (card-level formulas)

```bash
curl -s "https://$DOMO_INSTANCE/api/content/v1/cards?urns=$CARD&parts=formulas" \
  -H "$AUTH_HEADER" \
 | python3 -c "
import json, sys
c = json.load(sys.stdin)[0]
fm = c.get('formulas') or {}
fm = fm.get('formulas', fm) if isinstance(fm, dict) else fm
items = fm.items() if isinstance(fm, dict) else enumerate(fm)
for _, f in items:
    if not isinstance(f, dict): continue
    print(f\"[{f.get('templateId','?')}] {f.get('name')}\")
    print('   ', ' '.join(str(f.get('formula','')).split())[:400])
    print()
"
```

Cards can also inherit **dataset-level** beast modes, which will not appear here. Fetch those separately:

```bash
curl -s "https://$DOMO_INSTANCE/api/data/v3/datasources/$DATASET_ID" -H "$AUTH_HEADER" \
 | python3 -c "
import json,sys
for f in (json.load(sys.stdin).get('properties',{}).get('formulas',{}).get('formulas',{}) or {}).values():
    print(f.get('name'), '->', ' '.join(str(f.get('formula','')).split())[:200])
"
```

> `DOMO_BEAST_MODE(n)` inside a formula references **another beast mode's `templateId`**, not a column.
> Resolve it against the `templateId` values printed above or the formula will read as nonsense.

---

## Recipe 5: Lineage — what feeds this card

```bash
curl -s "https://$DOMO_INSTANCE/api/content/v1/cards?urns=$CARD&parts=datasources" \
  -H "$AUTH_HEADER" \
 | python3 -c "
import json, sys
for ds in json.load(sys.stdin)[0].get('datasources', []):
    print(f\"{ds['dataSourceId']}  {ds['dataSourceName']}  ({ds.get('dataType')})\")
"
```

Then hand off — see [Chaining](#chaining-with-the-other-domo-skills).

### Card's full column universe

Every column the card *could* use, including inherited beast modes (83 columns is typical):

```bash
curl -s "https://$DOMO_INSTANCE/api/content/v1/cards/$CARD/details" -H "$AUTH_HEADER" \
 | python3 -c "
import json, sys
defs = json.load(sys.stdin)['columns']['definitions']
print(f'{len(defs)} columns available')
for c in defs:
    print(f\"  {c['name']}  ({c['type']}{', aggregatable' if c.get('isAggregatable') else ''})\")
"
```

Contrast this with Recipe 3, which shows only the columns actually *displayed*.

### List cards on a page

```bash
curl -s "https://$DOMO_INSTANCE/api/content/v1/pages/$PAGE_ID/cards" -H "$AUTH_HEADER" \
 | python3 -c "
import json, sys
for c in json.load(sys.stdin):
    print(f\"  {c['urn']:>12} | {c['type']:6} | {c['title']}\")
"
```

---

## Chaining with the other Domo skills

Card IDs and dataset IDs are the join keys between all four Domo skills. Authenticate **once** per bash
block and reuse `$AUTH_HEADER` across skills.

**Forward — diagnosing a wrong number on a card:**

1. `domo-card` Recipe 2 → the rendered numbers, beast modes, and `dataSourceId`.
2. **`domo-get-dataset-schema`** with that `dataSourceId` → real column names and types.
3. **`domo-query-dataset`** → recompute the card's number in SQL and compare against Recipe 3's `rows`.
   A mismatch localizes the bug to the card (beast mode / filter / date grain); a match pushes it upstream.
4. **`domo-dataflow`** → inspect the ETL producing that dataset.

**Reverse — impact analysis before changing a dataflow:**

1. **`domo-dataflow`** → the dataflow's output dataset IDs.
2. `domo-card` Recipe 1, filtering hits on `dataSourceIds` → every card that breaks if you change it.

---

## Gotchas

All verified against a live instance on 2026-08-04.

- **`parts=all` is a silent no-op** on `GET /api/content/v1/cards?urns=`. It returns only base fields
  (`urn`, `id`, `type`, `title`, `ownerId`, …). Parts must be named explicitly.
- **Valid `parts` values:** `metadata`, `formulas`, `datasources`, `drillPath`, `slicers`,
  `certification`, `owners`, `subscriptions`, `domoapp`, `conditionalFormats`. Anything else
  (`properties`, `library`, `dateGrain`, `problems`, `masonData`, `summary`) is accepted but adds nothing.
- **`includeQueryInfo=true` never returns a `queryInfo` key.** The parameter is accepted and ignored, as
  is `parts` on the `/data` endpoint. Axis and aggregation info comes from `mappings` + `metadata`.
- **A `200` does not mean success on `/v1/*` paths.** `https://$DOMO_INSTANCE/v1/cards` returns HTTP 200
  with a ~2,800-byte HTML SPA shell. Confirm the body parses as JSON.
- **The public API is unavailable.** `https://api.domo.com/v1/cards` returns `401` with a developer token;
  it needs OAuth2 client-credentials this project does not have.
- **`GET /api/content/v1/cards/{id}` returns `405`.** Use the `?urns=` query form instead.
- **`POST /api/content/v1/cards/search` returns `405`.** Use `POST /api/search/v1/query` (Recipe 1).
- **Card titles live in `title`,** not `name`, in search results. `name` is always `null`.
- **Use `python3`, not `python`** — `python` is absent on macOS by default.
- `urns=` accepts a comma-separated list, so several cards can be fetched in one call.

---

## Endpoint reference

| Purpose | Method | Endpoint |
| :--- | :--- | :--- |
| Find card by name | POST | `/api/search/v1/query` (body `entityList:[["card"]]`) |
| Card metadata + parts | GET | `/api/content/v1/cards?urns={csv}&parts={csv}` |
| Rendered data | POST | `/api/content/v1/cards/{id}/data` (body `{}`) |
| Full column universe | GET | `/api/content/v1/cards/{id}/details` |
| Cards on a page | GET | `/api/content/v1/pages/{pageId}/cards` |
| Dataset beast modes | GET | `/api/data/v3/datasources/{datasetId}` |
