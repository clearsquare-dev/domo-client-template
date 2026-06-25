---
name: domo-dataflow
description: Read, understand, and update Domo Magic ETL dataflows. Use this skill whenever the user mentions a dataflow by name or ID, wants to inspect what a dataflow does, needs to modify transformation logic (add/remove columns, change join keys, update ReplaceString mappings, add filter conditions), or wants to understand the data lineage of a Domo ETL pipeline. Trigger even if the user just says something like "look at the customer dataflow" or "update the region mappings in the dataflow" — any reference to a Domo dataflow warrants this skill.
---

# domo-dataflow

Fetch, interpret, and modify Domo Magic ETL dataflows using the internal API.

---

## Auth

Always authenticate first using the pattern in CLAUDE.md.

```bash
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
```

---

## Step 1 — Resolve the Dataflow

**If you have an ID already**, skip to Step 2.

**If you have a name**, search for it:

```bash
curl -s "https://$DOMO_INSTANCE/api/dataprocessing/v1/dataflows?limit=50&offset=0" \
  -H "$AUTH_HEADER" \
  | python3 -c "
import json, sys
flows = json.load(sys.stdin)
for f in flows:
    if '<search_term>' in f['name'].lower():
        print(f['id'], '|', f['name'])
"
```

Paginate with `offset=50`, `offset=100`, etc. if needed (results are capped at 50 per page). Pick the correct ID.

---

## Step 2 — Fetch the Dataflow Definition

```bash
curl -s "https://$DOMO_INSTANCE/api/dataprocessing/v1/dataflows/<id>" \
  -H "$AUTH_HEADER" \
  | python3 -m json.tool > /tmp/dataflow_<id>.json
cat /tmp/dataflow_<id>.json
```

> Always save the raw JSON to a temp file. You'll need it as the base for any update.

---

## Step 3 — Understand the Dataflow

Parse and summarize the flow for the user. The key sections are:

| Section | What it contains |
|---|---|
| `inputs[]` | Source datasets by `dataSourceId` and `dataSourceName` |
| `outputs[]` | Output dataset name and `versionChainType` (`REPLACE` = full overwrite) |
| `actions[]` | The ordered list of transformation tiles |
| `triggerSettings` | What causes the flow to run (dataset update events, schedules) |
| `lastExecution` | Most recent run status and timestamps |

### Action types and what to look for

| Type | Key fields |
|---|---|
| `LoadFromVault` | `dataSourceId`, `name`, `columnSettings` (type overrides), `executeFlowWhenUpdated` |
| `SelectValues` | `fields[]` — each has `name`, `rename`, `remove` |
| `Metadata` | `fields[]` — same as SelectValues; used for renaming/dropping columns |
| `Filter` | `filterList[]` — two modes: (1) structured: `leftField`, `operator`, `rightValue.value`; (2) expression: `expression` contains raw SQL string (when `leftField` is null) |
| `ReplaceString` | `fields[]` — each has `inStreamName`, `replaceString`, `replaceByString`, `useRegex`, `caseSensitive` |
| `MergeJoin` | `joinType` (`LEFT OUTER`, `INNER`, etc.), `step1`/`step2`, `keys1`/`keys2`, `schemaModification2[]` (rename/drop cols from the right side) |
| `PublishToVault` | `dataSource.name` (output dataset name), `versionChainType` |
| `ExpressionEvaluator` | `expressions[]` — each has `fieldName` (output col name) and `expression` (SQL/formula string, e.g. `CONCAT(TRIM(\`fname\`), ' ', TRIM(\`lname\`))`) |
| `GroupBy` | `groups[]` (columns to group by, each has `name`), `fields[]` (aggregated output columns, each has `name` and `expression` like `MIN(\`date\`)`, `COUNT(...)`) |
| `Unique` | `fields[]` — columns to deduplicate on (each has `name`, `caseInsensitive`); keeps first row per unique combination |
| `WindowAction` | `groupRules[]` (PARTITION BY columns), `orderRules[]` (ORDER BY columns with `ascending`), `additions[]` (output cols, each has `name` and `operation.operationType` like `ROW_NUMBER`, `RANK`, `SUM`) |
| `Constant` | `fields[]` — each adds a hardcoded column: `name` (output col), `value` (literal string), `type` (`STRING`, `LONG`, etc.), `expr` (null if literal). Used to tag rows with a static label (e.g. office name) before a UnionAll. |
| `UnionAll` | `inputs[]` (list of tile IDs to stack), `unionType` (`INCLUDE_ALL` = keep all rows including duplicates), `schemaSource` (tile ID whose column list defines the output schema), `strict` (false = tolerate missing cols) |

When summarizing, describe the flow as a pipeline:
- What datasets flow in (from `inputs`)
- Each transformation in order (follow `dependsOn` chains)
- What comes out and where it goes

### Handling unknown tile types

The tile registry above is not exhaustive — Domo adds new Magic ETL tile types over time. When you encounter a `type` that is not in the table above:

1. **Inspect the raw action JSON** — look at the fields beyond `type`, `id`, `name`, `dependsOn`, `gui`, `settings`, and `tables` (those are common to all tiles). The unique fields are the ones that matter.
2. **Infer the behavior** from the field names and values. For example: `fields[]` with `expression` suggests a formula tile; `inputs[]` (plural) suggests it fans in from multiple streams.
3. **Display it in the pipeline summary** with your best-effort description, clearly marked as `[UNKNOWN TYPE]` so the user can see it.
4. **After the summary, flag it to the user** — show the raw unique fields and ask: *"I encountered a tile type I haven't seen before: `TypeName`. Here's what its JSON looks like — want me to add it to the skill so I'll recognize it in the future?"*
5. **If the user says yes**, update the `Action types and what to look for` table in this skill file (`.claude/skills/domo-dataflow/SKILL.md`) with a new row describing the type and its key fields.

This keeps the registry growing organically as we explore more dataflows.

---

## Step 4 — Modify the Dataflow

**Only proceed if the user has explicitly asked for a change.** Before touching anything, give a pre-flight summary:
1. What you're changing (which tile, what field)
2. The dataflow ID
3. The potential impact (e.g., "this will add a new ReplaceString mapping to the Route Region column")

### How to edit safely

1. Load the saved JSON: `cat /tmp/dataflow_<id>.json`
2. Make the targeted change in Python (don't guess at the structure — read the actual action first)
3. Write the modified JSON to a new temp file: `/tmp/dataflow_<id>_updated.json`
4. PUT it back — the entire definition must be sent (Domo replaces the whole record):

```bash
curl -s -X PUT "https://$DOMO_INSTANCE/api/dataprocessing/v1/dataflows/<id>" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d @/tmp/dataflow_<id>_updated.json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK' if 'id' in d else d)"
```

### Common edit patterns

**Add a ReplaceString entry** (e.g., normalize a new region name):
```python
import json

with open('/tmp/dataflow_<id>.json') as f:
    flow = json.load(f)

# Find the ReplaceString tile by name or type
for action in flow['actions']:
    if action['type'] == 'ReplaceString' and action['name'] == 'Replace Text':
        action['fields'].append({
            "inStreamName": "Route Region",
            "outStreamName": None,
            "useRegex": False,
            "replaceString": "New Name - Person",
            "replaceByString": "New Name",
            "setEmptyString": False,
            "replaceFieldByString": None,
            "wholeWord": False,
            "caseSensitive": False
        })

with open('/tmp/dataflow_<id>_updated.json', 'w') as f:
    json.dump(flow, f, indent=2)
```

**Add a column to SelectValues**:
```python
for action in flow['actions']:
    if action['id'] == '<tile-id>':
        action['fields'].append({
            "name": "newColumnName",
            "rename": "",
            "type": None,
            "dateFormat": None,
            "settings": {},
            "remove": False
        })
```

**Remove a column (set `remove: true`)**:
```python
for action in flow['actions']:
    if action['id'] == '<tile-id>':
        for field in action['fields']:
            if field['name'] == 'columnToRemove':
                field['remove'] = True
```

**Change a filter condition**:
```python
for action in flow['actions']:
    if action['type'] == 'Filter':
        for f in action['filterList']:
            if f['leftField'] == 'active':
                f['rightValue']['value'] = '1'  # change the value being compared
```

---

## Important Constraints

- **Never use `?hydrate=full`** on the dataflows endpoint — it causes 400 errors.
- **PUT always replaces the entire definition** — never send a partial payload.
- **Always GET the current state** before constructing a PUT — never edit from memory or a stale file.
- **Do not execute the dataflow** (POST to `/executions`) unless the user explicitly asks.
- Follow the read-only default from CLAUDE.md — summarize and confirm before any write.
