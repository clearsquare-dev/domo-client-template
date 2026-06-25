# Dashboard & Card Building Patterns

Patterns for building dashboards and cards that complement your custom app development. Covers native Domo cards, Beast Mode calculated fields, page layouts, and embedding custom apps as cards on dashboard pages.

## Card Types

### When to Use Each Type

| Card Type | API Value | Best For | Data Shape |
|-----------|-----------|----------|------------|
| KPI / Sumo | `kpi` | Single headline number | 1 metric, optional comparison |
| Vertical Bar | `badge_vert_bar` | Category comparison | 1 dimension, 1-3 metrics |
| Horizontal Bar | `badge_horiz_bar` | Ranked lists, long labels | 1 dimension, 1-3 metrics |
| Stacked Bar | `badge_vert_stackedbar` | Part-of-whole by category | 1 dimension, 1 metric, 1 series |
| Line / Trendline | `badge_line` | Trends over time | 1 date, 1-3 metrics |
| Area | `badge_filled_line` | Volume trends over time | 1 date, 1-3 metrics |
| Pie / Donut | `badge_pie` | Proportions (max 6-8 slices) | 1 dimension, 1 metric |
| Table | `badge_table` | Detail data, drill-down | Any number of columns |
| Heatmap | `badge_heatmap` | Two-dimensional patterns | 2 dimensions, 1 metric |
| Scatter | `badge_scatter` | Correlation analysis | 2 metrics, optional size/color |
| Gauge | `badge_radial_gauge` | Progress toward goal | 1 metric with target |
| Bullet | `badge_bullet` | Actual vs. target | 1 metric with target |

### Selection Heuristics

- **One number to highlight?** → KPI card
- **Comparing categories?** → Vertical bar (< 10 items) or horizontal bar (> 10 items or long labels)
- **Showing change over time?** → Line chart (2-5 series) or area chart (1-2 series)
- **Part of a whole?** → Pie/donut (2-6 slices) or stacked bar (more categories)
- **Showing detailed records?** → Table card
- **Comparing two metrics?** → Scatter plot

## Beast Mode Calculated Fields

Beast Modes extend datasets with computed columns without modifying the underlying data. They are defined on a dataset and available to any card that uses that dataset.

### Syntax Rules

**Column references:** Always use backticks
```
`Revenue`
`Date Column With Spaces`
```

**String comparisons:** Use single quotes
```
CASE WHEN `Status` = 'Active' THEN 1 ELSE 0 END
```

**Aggregation functions:**
```
SUM(`Revenue`)
COUNT(DISTINCT `Customer ID`)
AVG(`Score`)
MIN(`Date`)
MAX(`Amount`)
```

### Common Formula Patterns

**Percent of Total:**
```
SUM(`Revenue`) / SUM(SUM(`Revenue`)) * 100
```

**Year-over-Year Change:**
```
(SUM(`Revenue`) - SUM(IFNULL(`Revenue_LY`, 0)))
/ NULLIF(SUM(IFNULL(`Revenue_LY`, 0)), 0) * 100
```

**Conditional Aggregation:**
```
SUM(CASE WHEN `Status` = 'Won' THEN `Amount` ELSE 0 END)
```

**Date Bucketing:**
```
CASE
  WHEN DATEDIFF(CURDATE(), `Created Date`) <= 30 THEN 'Last 30 Days'
  WHEN DATEDIFF(CURDATE(), `Created Date`) <= 90 THEN 'Last 90 Days'
  ELSE 'Older'
END
```

**Status Indicators:**
```
CASE
  WHEN `Score` >= 80 THEN 'Green'
  WHEN `Score` >= 60 THEN 'Yellow'
  ELSE 'Red'
END
```

**NULL Handling:**
```
IFNULL(`Revenue`, 0)
COALESCE(`Primary`, `Secondary`, 'Unknown')
```

### Aggregate vs. Row-Level Beast Modes

This distinction is critical for card wiring:

| Type | Contains | Card Aggregation |
|------|----------|-----------------|
| **Aggregate** | `SUM(`, `AVG(`, `COUNT(`, `MIN(`, `MAX(` | Do NOT set aggregation on the card column |
| **Row-level** | No aggregate functions (e.g., `` `Revenue` - `Cost` ``) | MUST set aggregation on the card column |

Getting this wrong causes double aggregation (`SUM(SUM(...))`) which produces wrong numbers or "Bad Request" errors.

### Validation

Always validate Beast Mode formulas before creating them:

```
beast_mode_validate(dataset_id, formula)
```

Common validation failures:
- Column name doesn't match exactly (case-sensitive, backtick-quoted)
- Function name misspelled (`DATEDIFF` not `DATE_DIFF`)
- Nested aggregation in wrong context

### Name Conflict Prevention

Beast Mode names must not conflict with existing dataset column names or other Beast Modes. Before creating:

1. Check dataset schema for column names
2. Check existing Beast Modes on the dataset
3. If a conflict exists, prefix the name (e.g., "Calc: Delivery %" instead of "Delivery %")

## Page Layout

### The 60-Unit Grid

Domo v2 page layouts use a 60-unit-wide grid. Cards are positioned with `x`, `y`, `width`, and `height` values.

```
|<----------------------- 60 units ----------------------->|
|     12     |     12     |     12     |     12     |  12  |
|  KPI Card  |  KPI Card  |  KPI Card  |  KPI Card  | KPI |
|------------|------------|------------|------------|------|
|          40 units            |       20 units            |
|     Main Chart               |    Side Chart            |
|------------------------------|--------------------------|
|                    60 units                              |
|              Full-Width Table                            |
|----------------------------------------------------------|
```

### Common Layout Patterns

**5 KPI cards across the top:**
```json
[
  { "cardId": 1, "x": 0,  "y": 0, "width": 12, "height": 6 },
  { "cardId": 2, "x": 12, "y": 0, "width": 12, "height": 6 },
  { "cardId": 3, "x": 24, "y": 0, "width": 12, "height": 6 },
  { "cardId": 4, "x": 36, "y": 0, "width": 12, "height": 6 },
  { "cardId": 5, "x": 48, "y": 0, "width": 12, "height": 6 }
]
```

**2/3 + 1/3 split:**
```json
[
  { "cardId": 1, "x": 0,  "y": 0, "width": 40, "height": 20 },
  { "cardId": 2, "x": 40, "y": 0, "width": 20, "height": 20 }
]
```

**Equal thirds:**
```json
[
  { "cardId": 1, "x": 0,  "y": 0, "width": 20, "height": 20 },
  { "cardId": 2, "x": 20, "y": 0, "width": 20, "height": 20 },
  { "cardId": 3, "x": 40, "y": 0, "width": 20, "height": 20 }
]
```

**Full-width card:**
```json
[
  { "cardId": 1, "x": 0, "y": 0, "width": 60, "height": 20 }
]
```

### Card Sizing (v1 Pages)

For v1 pages without programmatic layout, use card sizes:

| Size | API Value | Visual Width | Use For |
|------|-----------|-------------|---------|
| Small | *(default)* | ~200px (1/6 page) | KPI numbers only |
| Medium | `"medium"` | ~300px (1/4 page) | KPI cards, small charts |
| Large | `"large"` | ~434px (1/3 page) | Standard charts |
| Full | `"full"` | ~1300px (full page) | Tables, hero charts |

### v1 vs. v2 Pages

| Feature | v1 | v2 (Design Layout) |
|---------|----|--------------------|
| Card positioning | Creation order | Programmatic (x, y, w, h) |
| Grid system | Auto-flow | 60-unit grid |
| Resize | Card size presets | Pixel-precise |
| Rearrange | Drag-drop only | API `layout_set` |
| Ghost slots on delete | Yes (cannot remove) | No |

**Converting v1 to v2:**
```
layout_convert(page_id)  # Enables design layout mode
```

## App Card Creation

Custom Apps (built with `da new`, published with `domo publish`) can be placed on dashboard pages as cards alongside native Domo cards.

### Placing an App on a Page

After publishing your app (which creates a design ID), use MCP tools to place it:

```
# 1. Find your app's design ID
procode_design_list()  # Lists all app designs with IDs

# 2. Create a page (or use an existing one)
page_create(title="My Dashboard")

# 3. Place the app as a card
app_card_create(design_id="app-uuid", page_id=12345)

# 4. Set the layout (v2 pages)
layout_set(page_id=12345, positions=[
  { "cardId": appCardId, "x": 0, "y": 0, "width": 60, "height": 30 }
])
```

### Mixing App Cards with Native Cards

A common pattern is placing your custom app alongside native KPI cards and charts:

```json
[
  { "cardId": "kpi-1",   "x": 0,  "y": 0,  "width": 15, "height": 6 },
  { "cardId": "kpi-2",   "x": 15, "y": 0,  "width": 15, "height": 6 },
  { "cardId": "kpi-3",   "x": 30, "y": 0,  "width": 15, "height": 6 },
  { "cardId": "kpi-4",   "x": 45, "y": 0,  "width": 15, "height": 6 },
  { "cardId": "app-card", "x": 0,  "y": 6,  "width": 40, "height": 24 },
  { "cardId": "chart-1",  "x": 40, "y": 6,  "width": 20, "height": 12 },
  { "cardId": "chart-2",  "x": 40, "y": 18, "width": 20, "height": 12 }
]
```

This creates a layout with KPI cards across the top, your custom app taking 2/3 of the main area, and native charts filling the right column.

## Dashboard Design Principles

### Cognitive Load

- Limit to 7-10 cards per page (align with working memory capacity)
- Use progressive disclosure: summary page → detail pages
- Group related cards visually with whitespace and alignment

### Visual Hierarchy

Follow the "inverted pyramid" pattern:

1. **Top row:** KPI hero metrics (the numbers executives check first)
2. **Middle section:** Primary analysis charts (trends, comparisons)
3. **Bottom section:** Detail tables and supporting charts

### KPI Card Placement

- Always place KPI cards in the first row
- Use 4-5 cards across for the best visual balance
- Include comparison indicators (vs. prior period, vs. target)
- Use consistent formatting: same number of decimal places, same units

### Color Usage

- Use your organization's brand colors
- Reserve red/green for actual good/bad indicators (not decoration)
- Limit to 5-7 distinct colors per chart
- Use color consistently: if "Region A" is blue on one chart, it should be blue on all charts

### Naming Conventions

- Card titles should describe the insight, not just the data
- Good: "Revenue by Region (YTD)" — tells you what, how, and when
- Bad: "Chart 1" or "Data" — no context
- Include the time period in the title when relevant

## MCP Tool Automation Reference

### Creating a Complete Dashboard

```
# Step 1: Create the page
page_create(title="Q4 Sales Dashboard")

# Step 2: Create Beast Modes for calculated fields
beast_mode_validate(dataset_id, "SUM(`Revenue`) / SUM(SUM(`Revenue`)) * 100")
beast_mode_create(dataset_id, name="Revenue %", formula="...")

# Step 3: Create KPI cards
card_create_full(page_id, dataset_id, chart_type="kpi", columns=[...])

# Step 4: Create analysis cards
card_preview(dataset_id, "badge_vert_bar", columns=[...])  # Preview first
card_create_full(page_id, dataset_id, chart_type="badge_vert_bar", columns=[...])

# Step 5: Place a custom app
app_card_create(design_id, page_id)

# Step 6: Set layout
layout_convert(page_id)  # If needed
layout_set(page_id, positions=[...])

# Step 7: Verify
page_cards(page_id)
card_render_check(card_id)  # For each card
```

### Key Tools for Dashboard Building

| Task | Tool |
|------|------|
| Create a page | `page_create` |
| Create a chart card | `card_create_full` |
| Preview before creating | `card_preview` |
| Create a calculated field | `beast_mode_create` |
| Validate a formula | `beast_mode_validate` |
| Set card positions | `layout_set` |
| Place a custom app | `app_card_create` |
| Set card size (v1) | `card_size_set` |
| Verify card renders | `card_render_check` |

## Best Practices

1. **Preview before creating** — Always use `card_preview` to verify chart configuration
2. **Create Beast Modes first** — Cards that reference uncreated Beast Modes fail silently
3. **Validate formulas** — Use `beast_mode_validate` before `beast_mode_create`
4. **Check for name conflicts** — Beast Mode names must not conflict with column names
5. **Use v2 layouts** — Programmatic positioning via `layout_set` is more reliable than v1 card ordering
6. **Render-check after creation** — Use `card_render_check` to verify cards display correctly
7. **Build top-to-bottom** — On v1 pages, create cards in visual order (KPIs first, tables last)
