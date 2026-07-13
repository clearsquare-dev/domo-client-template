# Reacting to Dashboard Filter Cards

How to make a Custom App respond to *native* Domo filter cards (dropdown,
radio, category) placed elsewhere on the same dashboard page — without the
user touching anything inside the app itself.

This is different from the app's own internal filter controls (dropdowns you
build yourself, filtered client-side per `dataset-best-practices.md`). This
doc covers listening to Domo's page-level filter broadcast.

## The API

```js
const subscribe = typeof domo.onFiltersUpdated === 'function'
  ? domo.onFiltersUpdated   // current name (domo.js v5 / ryuu.js)
  : domo.onFiltersUpdate;   // older name, some domo.js/ryuu.js versions

subscribe(function (filters) {
  // filters: array of filter objects, see shape below
});
```

Register this once, during app init, alongside your normal data fetch. It
fires whenever **any** filter card on the page changes — not just ones
someone explicitly "attached" to your app. Domo broadcasts to every
listening card; your callback is responsible for ignoring columns it doesn't
care about.

Confirmed working (2026-07): a filter card living in a separate KPI card on
the same dashboard page successfully drove another app's chart, with no
dashboard-side linking step beyond the filter card and the app's SQL sharing
the same underlying column name, and no `manifest.json` changes required.
Confirmed in one project so far — re-verify if you hit different behavior.

## Filter object shape

```js
{
  column: 'location_rollup',   // raw dataset column the filter card is bound to
  operator: 'IN',              // filter operator
  values: ['Downtown', 'Uptown'], // always strings, even for numeric/date columns
  dataType: 'STRING',          // STRING | NUMERIC | DATE | DATETIME
  dataSourceId: '46d91556-...',// source dataset id (optional)
  label: 'Location',           // display label (optional)
}
```

- `column` is the **exact dataset column name**, not necessarily your app's
  internal field name. You have to know (or ask) what column the client's
  filter card is actually bound to — don't guess it from the card's on-screen
  label. Confirm with whoever built the dashboard/filter card.
- An empty `values` array means the filter was cleared back to "all" — treat
  that as "no filter active," not as "match nothing."
- Only react to `column` values you recognize; a dashboard tab commonly has
  filter cards for other KPIs on the same page that your app should ignore.

## Wiring pattern

Pairs naturally with the fetch-once/filter-client-side pattern in
`dataset-best-practices.md`: fetch the full dataset once at load, then filter
in JS on every trigger (internal dropdown change OR incoming Domo filter) —
this avoids re-querying SQL on every filter card tick and keeps updates
instant.

```js
const state = {
  rawRows: [],
  domoFilters: { location: null }, // null = no page filter active
};

function handleDomoFiltersUpdated(filters) {
  const locationFilter = filters.find(f => f.column === 'location_rollup');
  state.domoFilters.location = (locationFilter && locationFilter.values.length)
    ? locationFilter.values
    : null;
  render();
}

function getFilteredRows() {
  return state.rawRows.filter(r =>
    !state.domoFilters.location || state.domoFilters.location.includes(r.location)
  );
}

// In init(), after the initial fetch + render:
const subscribe = typeof domo.onFiltersUpdated === 'function' ? domo.onFiltersUpdated : domo.onFiltersUpdate;
if (typeof subscribe === 'function') subscribe(handleDomoFiltersUpdated);
```

If the app also has its own internal filter dropdowns, combine them with the
Domo filter state using AND (both narrow the data together), rather than
letting one override the other — that's the behavior a user expects from two
independent filter controls.

## Unconfirmed / verify per-project

- Whether `onFiltersUpdated` alone is enough to get a smooth in-place update,
  or whether Domo *also* does a hard iframe reload on top of it in some
  configurations. Worked cleanly with just the listener in the one case
  verified so far — but test this directly in `domo dev` on the target
  dashboard rather than assuming.
- Exact behavior for `operator` values other than `IN` (e.g. date-range
  `BETWEEN` filter cards) hasn't been exercised yet — the `values` array
  membership check above only covers simple inclusion filters.

## Sources

- [domo.js (ryuu.js) — Domo Developer Portal](https://developer.domo.com/docs/tools/domo-js)
- [Domo.js (Ryuu.js) v5 — Domo](https://www.domo.com/docs/portal/Apps/App-Framework/Tools/domo-js-v5)
- [How can I use domo.onFiltersUpdate to stop App refresh while still getting filtered data? — Domo Community Forum](https://community-forums.domo.com/main/discussion/56675/how-can-i-use-domo-onfiltersupdate-to-stop-app-refresh-while-still-getting-filtered-data)
