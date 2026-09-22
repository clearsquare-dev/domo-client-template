#!/usr/bin/env python3
"""
Builders for out-of-the-box Domo KPI card bodies (PUT /api/content/v3/cards/kpi?pageId=).

    from cards_lib import card, col, bcol, cdist, month_item, flt, this_year, last_months, bm, FMT

Mapping rules the page renderer enforces (the API will happily store the wrong thing):
  single value      one aggregated VALUE
  chart, 1 measure  ITEM + VALUE (+ SERIES dimension)
  chart, 2+ measures ITEM + every measure as SERIES (with aggregation); no VALUE
  table             every column VALUE; non-aggregated ones are grouped automatically here
  selector          ITEM only
"""
import uuid

FMT = {
    "usd":     {"type":"currency","format":"###,###","commas":True,"percentMultiplied":True,"precision":0,"currency":"$"},
    "usd_abbr":{"type":"abbreviated","format":"$0.0"},
    "num":     {"type":"number","format":"###,###","commas":True,"precision":0},
    "year":    {"type":"number","format":"0","commas":False,"precision":0},        # stops LONG years showing as "$2,023"
    "pct":     {"type":"percent","format":"###,###.0%","commas":True,"percentMultiplied":True,"precision":1,"percent":True},
}

def col(column, mapping="VALUE", aggregation=None, alias=None, fmt=None, **kw):
    c = {"column": column, "mapping": mapping}
    if aggregation: c["aggregation"] = aggregation
    if alias: c["alias"] = alias
    if fmt: c["format"] = fmt
    c.update(kw); return c

def cdist(column, alias, mapping="VALUE"):
    """COUNT DISTINCT (the aggregation name COUNT_DISTINCT is rejected)."""
    return col(column, mapping, "COUNT", alias, FMT["num"], distinct=True)

def month_item(): return {"column": "CalendarMonth", "calendar": True, "mapping": "ITEM"}

def flt(column, values, dtype="string"):
    return {"column": column, "values": values, "filterType": "LEGACY", "operand": "IN", "dataType": dtype}

def this_year(date_col):
    return {"column": {"column": date_col, "exprType": "COLUMN"}, "dateTimeRange": {"dateTimeRangeType": "INTERVAL_OFFSET", "interval": "YEAR", "offset": 0, "count": 0}}

def last_months(date_col, n):
    return {"column": {"column": date_col, "exprType": "COLUMN"}, "dateTimeRange": {"dateTimeRangeType": "ROLLING_PERIOD", "interval": "MONTH", "offset": 0, "count": n}}

def bm(name, formula, dtype="DOUBLE"):
    """Card-level beast mode. No templateId/legacyId/formulaId: two formulas sharing templateId -1 are rejected."""
    fid = "calculation_" + str(uuid.uuid4())
    return {"id": fid, "name": name, "formula": formula, "query": formula, "status": "VALID", "dataType": dtype,
            "persistedOnDataSource": False, "initialPersistedOnDataSource": False, "isAggregatable": False, "bignumber": False,
            "nonAggregatedColumns": [], "nonAggregatedExpressions": [], "variable": False, "isCalculation": True, "saved": False,
            "cacheWindow": "non_dynamic", "containsAggregation": True, "containsAnalytic": False, "invalidColumns": [],
            "formulaTemplateDependencies": [], "formulaDependencies": [], "columnPositions": [], "isControlled": False}

def bcol(formula, mapping="VALUE", alias=None, fmt=None):
    c = {"formulaId": formula["id"], "mapping": mapping, "alias": alias or formula["name"]}
    if fmt: c["format"] = fmt
    return c

def is_measure(c): return bool(c.get("aggregation") or c.get("formulaId"))

def card(title, chart_type, columns, ds, date_col, filters=None, orderBy=None, dateRange=None, monthGrain=False,
         overrides=None, formulas=None, description="", limit=None):
    if chart_type == "badge_basic_table":
        columns = [dict(c, mapping="VALUE") for c in columns]                        # tables: everything is VALUE
    measures = [c for c in columns if is_measure(c)]
    if chart_type not in ("badge_basic_table", "badge_singlevalue") and not chart_type.endswith("_selector") and len(measures) > 1:
        columns = [dict(c, mapping="SERIES") if is_measure(c) else c for c in columns]   # multi-measure charts: measures are SERIES
        overrides = dict(overrides or {}, never_use_time_scale="true")
    groupBy = [{k: v for k, v in c.items() if k in ("column", "calendar")} for c in columns if not is_measure(c)]
    main = {"name": "main", "dataSourceId": ds, "columns": columns, "filters": filters or [], "orderBy": orderBy or [], "groupBy": groupBy,
            "fiscal": False, "projection": False, "distinct": False,
            "dateGrain": {"column": date_col, "dateTimeElement": "MONTH"} if monthGrain else {"column": date_col}}
    if dateRange: main["dateRangeFilter"] = dateRange
    if limit: main["limit"] = limit
    if chart_type.endswith("_selector"): bn_cols = [{"column": columns[0]["column"], "aggregation": "COUNT"}]
    else:
        v = measures[0]; bn_cols = [{k: x for k, x in v.items() if k != "mapping"}]  # big_number must have one aggregated column
    big = {"name": "big_number", "dataSourceId": ds, "columns": bn_cols, "filters": filters or [], "orderBy": [], "groupBy": [],
           "fiscal": False, "projection": False, "distinct": False, "limit": 1}
    if dateRange: big["dateRangeFilter"] = dateRange
    d = {"subscriptions": {"big_number": big, "main": main},
         "formulas": {"dsUpdated": [], "dsDeleted": [], "card": formulas or []},
         "annotations": {"new": [], "modified": [], "deleted": []}, "conditionalFormats": {"card": [], "datasource": []}, "controls": [],
         "segments": {"active": [], "create": [], "update": [], "delete": []},
         "charts": {"main": {"component": "main", "chartType": chart_type, "overrides": overrides or {}, "goal": None}},
         "dynamicTitle": {"text": [{"text": title, "type": "TEXT"}]},
         "dynamicDescription": {"text": ([{"text": description, "type": "TEXT"}] if description else []), "displayOnCardDetails": True},
         "chartVersion": "12", "inputTable": False, "noDateRange": False, "title": title, "description": description}
    return {"definition": d, "dataProvider": {"dataSourceId": ds}, "variables": True, "columns": False}
