---
name: domo-query-dataset
description: >
  Use this skill to query column values from a Domo dataset, optionally with filters. Triggers when the user wants to: fetch distinct values from a column, check what values exist in a filtered dataset, pull data from a Domo dataset to inform an ETL update, or inspect column values for a specific date range, location, or category.
---

# Domo Query Dataset

Query a Domo dataset using SQL via the `/api/query/v1/execute/{datasetId}` endpoint.

## Workflow

1. **Authenticate once** — set `$AUTH_HEADER` using the auth pattern in CLAUDE.md (uses `DOMO_ACCESS_TOKEN` if set in `.env`, otherwise falls back to a SID session). Re-use it for all subsequent calls in the same bash block.
2. **Check schema + query in one block** — pipe the schema check and query together so auth runs only once (see Fast Path below).
3. **Parse and present results**.

> Auth: follow the pattern in CLAUDE.md. If falling back to the legacy SID flow, SIDs expire after ~1 hour — re-run if you get a 401.

---

## Endpoint

```
POST https://{instance}.domo.com/api/query/v1/execute/{datasetId}
```

Always use `table` as the table name in SQL (not the dataset name or ID). Use a plain SQL string payload — the structured JSON query format causes 400/500 errors.

---

## Fast Path — Auth + Schema Check + Query in One Block

Authenticate once and reuse `$AUTH_HEADER` for both the schema check and the query. This avoids re-authenticating between skill steps.

```bash
# 1. Auth (from CLAUDE.md pattern)
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi

if [ -n "$DOMO_ACCESS_TOKEN" ]; then
  AUTH_HEADER="X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
else
  # Fallback: no DOMO_ACCESS_TOKEN set — use legacy SID session flow (expires ~1hr, re-run if 401)
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

# 2. Schema check — grep for relevant columns to confirm exact names/casing
curl -s -X POST "https://$DOMO_INSTANCE/api/query/v1/execute/{datasetId}" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM table LIMIT 1"}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for name, m in zip(d.get('columns',[]), d.get('metadata',[])):
    print(f'{name} ({m[\"type\"]})')
" | grep -i "{keyword}"

# 3. Query — reuse same $AUTH_HEADER, no re-auth needed
curl -s -X POST "https://$DOMO_INSTANCE/api/query/v1/execute/{datasetId}" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"sql": "YOUR SQL HERE"}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
rows = d.get('rows', [])
print(f'{len(rows)} rows')
for r in rows:
    print(r[0])
"
```

---

## SQL Patterns

### Distinct values for a column
```sql
SELECT DISTINCT OfficeName FROM table ORDER BY OfficeName LIMIT 1000
```

### Columns with spaces or special characters — use backticks
```sql
SELECT DISTINCT `Group 0 Name`, `Memo/Description` FROM table LIMIT 1000
```

### Filter by date range
```sql
SELECT DISTINCT `Memo/Description`
FROM table
WHERE Date BETWEEN '2026-03-01' AND '2026-03-31'
LIMIT 1000
```

### Filter by category + office
```sql
SELECT DISTINCT `Memo/Description`
FROM table
WHERE OfficeName = 'Washington'
  AND canonical_category_v2 = 'Corporate Structure'
LIMIT 1000
```

### Multiple filters
```sql
SELECT DISTINCT `Memo/Description`
FROM table
WHERE Date BETWEEN '2026-03-01' AND '2026-03-31'
  AND OfficeName = 'Washington'
  AND canonical_category_v2 = 'Corporate Structure'
  AND `Group 0 Name` = 'Digital Marketing Payroll'
LIMIT 1000
```

### Aggregation
```sql
SELECT OfficeName, SUM(Amount) AS total
FROM table
WHERE Date BETWEEN '2026-01-01' AND '2026-12-31'
GROUP BY OfficeName
ORDER BY total DESC
LIMIT 100
```

---

## Response Shape

```json
{
  "datasource": "{datasetId}",
  "columns": ["ColumnName"],
  "rows": [["value1"], ["value2"]],
  "numRows": 2,
  "numColumns": 1
}
```

`rows` is an array of arrays — `rows[i][j]` maps to column `j` for row `i`.

### Parse results with Python

```python
import json, sys
d = json.load(sys.stdin)
cols = d.get('columns', [])
rows = d.get('rows', [])
print(f"{len(rows)} rows")
for row in rows:
    print(dict(zip(cols, row)))
```

Or for a single-column distinct query:

```python
import json, sys
d = json.load(sys.stdin)
for row in d.get('rows', []):
    print(row[0])
```

---

## Full Example — Schema check + distinct values in one block

```bash
# Auth (CLAUDE.md pattern)
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi

if [ -n "$DOMO_ACCESS_TOKEN" ]; then
  AUTH_HEADER="X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
else
  # Fallback: no DOMO_ACCESS_TOKEN set — use legacy SID session flow (expires ~1hr, re-run if 401)
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

# Schema check — confirm column name/casing
curl -s -X POST "https://$DOMO_INSTANCE/api/query/v1/execute/{your-dataset-uuid}" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM table LIMIT 1"}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for name, m in zip(d.get('columns',[]), d.get('metadata',[])):
    print(f'{name} ({m[\"type\"]})')
" | grep -i "office"

# Query — reuse $AUTH_HEADER
curl -s -X POST "https://$DOMO_INSTANCE/api/query/v1/execute/{your-dataset-uuid}" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT DISTINCT OfficeName FROM table ORDER BY OfficeName LIMIT 1000"}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
rows = d.get('rows', [])
print(f'{len(rows)} unique values:')
for r in rows:
    print(f'  {r[0]}')
"
```

---

## Tips

- **Always check schema first** using `domo-get-dataset-schema` — column names are case-sensitive (`OfficeName` not `officename`).
- **Backtick columns** with spaces, slashes, or other special characters: `` `Group 0 Name` ``, `` `Memo/Description` ``.
- **Use `python3`** not `python` — `python` is not available on macOS by default.
- **`LIMIT 1000`** is safe for distinct lookups; increase if you expect more unique values.
- **Chain this skill** — get schema → build query → execute → present results.
