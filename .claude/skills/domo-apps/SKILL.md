---
name: domo-apps
description: Build, develop, and deploy Domo Custom Apps using vanilla JS, HTML, CSS, and Tailwind
---

# Domo Apps Development

Guide for building Domo Custom Apps using vanilla JS, HTML, and Tailwind CSS.

## Quick Start

### Install & Authenticate

```bash
# Install Domo CLI (if not installed)
npm install -g ryuu

# Verify
domo --version

# Login
domo login
```

### Create New App

```bash
# Non-interactive (use this — avoids prompt issues)
domo init -n "my-awesome-app" -t "hello world" --no-datasets
cd my-awesome-app
```

Available templates: `hello world`, `manifest only`, `basic chart`, `map chart`, `sugarforce`

This generates:
```
my-awesome-app/
├── manifest.json   # App config (name, size, dataset mappings)
├── index.html
├── app.js
├── app.css
└── thumbnail.png   # 300x300 placeholder (replace before going live)
```

⚠️ `domo init my-awesome-app` (positional arg) throws "too many arguments" — always use `-n` flag.

### Core Workflow

```bash
domo dev      # Local dev server at http://localhost:3000 (live reload)
domo publish  # Deploy to Domo
```

**Note:** `domo dev` proxies data through your authenticated CLI session — no `proxyId` needed for dataset queries.

## Standard App Structure

Every app follows this pattern:

**`index.html`** — layout skeleton only, no logic. Always include:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>My App</title>

  <!-- Tailwind CSS (default CSS engine) -->
  <script src="https://cdn.tailwindcss.com"></script>

  <!-- Domo JS — REQUIRED or domo is undefined -->
  <script src="https://cdn.domo.com/domo.js/1/domo.js"></script>
  <script
    src="https://unpkg.com/ryuu.js@4.6.0/dist/domo.js"
    integrity="sha384-YYsd9wQ+wDlUWhvpfGdptxmNYIqBC+52oJtWgPKJadbs3sSFTY/+ZotPbEHTTRWz"
    crossorigin="anonymous">
  </script>

  <link rel="stylesheet" href="app.css" />
</head>
<body>
  <!-- layout here -->
  <script src="app.js"></script>
</body>
</html>
```

**`app.css`** — CSS custom properties and layout classes not covered by Tailwind utilities.

**`app.js`** — all data fetching and DOM rendering logic.

## CSS: Tailwind + Custom Properties

Use Tailwind CDN for utility classes. Add an `app.css` for custom properties (colors, reusable layout grids, component styles):

```css
:root {
  --card-bg: #1e2130;
  --border: #2d3748;
  --accent: #00c274;
  --text-secondary: #8892a4;
}

/* Layout grids not easily expressed as Tailwind utilities */
.kpi-grid   { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.kpi-grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.table-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1.5rem; }

/* Custom component styles */
.kpi-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem;
}
```

## Querying Data

### SQL via domo.post (correct pattern)

```js
// ✅ Always use contentType: 'text/plain' with SQL as a plain string
domo.post('/sql/v1/myAlias', 'SELECT col1, col2 FROM table LIMIT 10', { contentType: 'text/plain' })
  .then(function(result) {
    // result.columns = ['col1', 'col2']
    // result.rows    = [['val1', 'val2'], ...]  ← arrays, not objects
    const rows = result.rows;
    rows.forEach(row => {
      const col1 = row[0];
      const col2 = row[1];
    });
  })
  .catch(err => console.error('Query failed:', err));
```

```js
// ❌ Wrong — will silently fail or return an error
domo.post('/sql/v1/myAlias', { sql: 'SELECT ...' }, { contentType: 'application/json' })
```

### Row-to-object mapping helper

```js
function toObjects(result) {
  return result.rows.map(r =>
    Object.fromEntries(result.columns.map((c, i) => [c, r[i]]))
  );
}

domo.post('/sql/v1/myAlias', SQL, { contentType: 'text/plain' })
  .then(result => {
    const rows = toObjects(result); // [{col1: 'val1', col2: 'val2'}, ...]
    // use rows...
  });
```

### Column names with dots (e.g. FieldRoutes datasets)

Use backticks, not double quotes:

```sql
SELECT `employee.fullName`, `subscription.annualRecurringValue`
FROM table
WHERE MONTH(`subscription.dateAdded`) = MONTH(CURRENT_DATE())
```

### Async/await pattern

```js
async function init() {
  try {
    const [monthData, todayData] = await Promise.all([
      domo.post('/sql/v1/myAlias', MONTH_SQL, { contentType: 'text/plain' }),
      domo.post('/sql/v1/myAlias', TODAY_SQL, { contentType: 'text/plain' }),
    ]);
    const m = toObjects(monthData);
    const t = toObjects(todayData);
    // render...
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
  } catch (err) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').textContent = 'Failed to load data. Please refresh.';
    document.getElementById('error').style.display = 'block';
    console.error(err);
  }
}

init();
```

## Manifest Configuration

After `domo init`, overwrite `manifest.json`:

```json
{
  "name": "my-app",
  "version": "1.0.0",
  "size": { "width": 3, "height": 3 },
  "fullpage": true,
  "datasetsMapping": [
    {
      "dataSetId": "your-dataset-uuid",
      "alias": "myAlias",
      "fields": [
        { "alias": "employeeFullName",   "columnName": "employee.fullName" },
        { "alias": "subscriptionAmount", "columnName": "subscription.annualRecurringValue" }
      ],
      "dql": null
    }
  ]
}
```

**Key fields:**
- `alias` — the string you use in `/sql/v1/<alias>`
- `fields` — declare every column your SQL queries touch; empty array will cause data access to fail for most column types
- `id` — auto-written by `domo publish`; keep it so future publishes update the same design
- `proxyId` — **only needed for AppDB collections**, NOT for dataset queries

⚠️ Do NOT add `proxyId` just to get `domo dev` working — dataset queries work without it.

## Loading & Error States

Always hide content until data loads:

```html
<div id="loading">Loading...</div>
<div id="error" style="display:none"></div>
<div id="app" style="display:none">
  <!-- your KPI cards, tables, etc. -->
</div>
```

## ⚠️ Version Management

Same version = overwrite. Increment `manifest.json` version before publishing if you want to keep a rollback copy:

```json
{ "version": "1.0.1" }
```

## Thumbnail

- File: `thumbnail.png` in the project root
- Size: exactly **300x300 pixels**

## Key Commands

```bash
domo init -n "name" -t "hello world" --no-datasets  # Create new app
domo dev           # Local dev server (live reload, no proxyId needed)
domo publish       # Deploy to Domo (run from project root)
domo login         # Authenticate to instance
domo --version     # Check CLI version
npm update -g ryuu # Update CLI
```

## Troubleshooting

**`domo` is not defined:**
- Missing the two CDN scripts in `<head>` — `domo init` does NOT include them automatically. Add both (domo.js + ryuu.js) as shown in the Standard App Structure above.

**Data queries fail / "Failed to load data":**
- Using wrong content type — must be `contentType: 'text/plain'` with SQL as a plain string
- Check browser console for the specific error from `domo.post`

**Columns with dots return no data:**
- Use backtick quoting: `` `employee.fullName` `` not `"employee.fullName"`

**`fields` array empty → no data:**
- Populate `fields` in `datasetsMapping` with every column your SQL references

**Publish creates new app instead of updating:**
- `id` is missing from manifest — `domo publish` writes it after first publish; keep it there

**`domo dev` port in use:**
- CLI auto-increments to next available port (3001, 3002, etc.)

## Reference Documentation

- `references/manifest-guide.md` - Complete manifest configuration
- `references/dataset-best-practices.md` - Dataset querying and SQL patterns
- `references/appdb.md` - AppDB collections and queries
- `references/cli-commands.md` - Complete CLI reference
- `references/deployment.md` - Multi-environment deployment
- `references/dashboard-card-building.md` - Dashboard cards, Beast Modes, layout
- `references/code-engine-patterns.md` - Code Engine serverless functions
- `references/mcp-tools-integration.md` - MCP tool automation for app development
- `examples/` - Example projects and patterns
