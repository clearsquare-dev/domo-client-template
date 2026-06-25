---
name: domo-get-dataset-schema
description: Use when you need to retrieve the column schema (names and types) for a Domo dataset, given either a dataset name or dataset ID. Applies to any Domo instance using the project auth pattern in CLAUDE.md.
---

# domo-get-dataset-schema

## Overview

Retrieves the full column schema (name + data type) for a Domo dataset. The standard metadata endpoint (`/api/data/v3/datasources/{id}`) does **not** return schema — use the SQL query endpoint instead.

## Inputs

- **Dataset ID** (UUID format, e.g. `ab4a80c2-b0ad-46f4-9e96-9a0ec1b7b0d9`) → skip to Step 2
- **Dataset name** (partial or full string) → start at Step 1

---

## Step 1: Resolve Name → ID

```bash
curl -s -G "https://$DOMO_INSTANCE/api/data/v3/datasources" \
  --data-urlencode "nameLike=<name>" \
  --data-urlencode "limit=10" \
  -H "$AUTH_HEADER" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for ds in d.get('dataSources', []):
    print(ds['id'], '|', ds['name'])
"
```

> Use `curl -G` with `--data-urlencode` — dataset names often contain spaces and hyphens that break inline query strings.

Pick the correct ID from the results, then proceed to Step 2.

---

## Step 2: Fetch Schema via SQL Query

```bash
curl -s -X POST "https://$DOMO_INSTANCE/api/query/v1/execute/<datasetId>" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM table LIMIT 1"}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
cols = d.get('columns', [])
meta = d.get('metadata', [])
print(f'Total columns: {len(cols)}')
print()
for name, m in zip(cols, meta):
    print(f'  {name} ({m[\"type\"]})')
"
```

### Response fields

| Field | Description |
|-------|-------------|
| `columns` | List of column name strings |
| `metadata` | Parallel list of objects; use `metadata[i]['type']` for data type |

### Common types

`STRING`, `LONG`, `DOUBLE`, `DATETIME`, `DATE`

---

## Auth

Authenticate using the pattern in CLAUDE.md before running any curl calls, setting `$AUTH_HEADER` (either `X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN` if set in `.env`, or the legacy `X-Domo-Authentication: $SID` fallback otherwise). SIDs expire after ~1 hour — re-run the fallback if you get a 401. When chaining with `domo-query-dataset`, authenticate once and reuse `$AUTH_HEADER` across both the schema check and the query in the same bash block.

## Common Mistakes

- **Using the metadata endpoint for schema** — `/api/data/v3/datasources/{id}` returns `columnCount` but not column definitions. Always use the SQL endpoint.
- **Wrong table alias** — Always use `table` (not the dataset name) in your SQL string.
- **Indexing `columns` as objects** — `columns` is a list of strings, not dicts. Types come from `metadata`.