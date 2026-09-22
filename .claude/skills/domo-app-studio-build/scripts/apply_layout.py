#!/usr/bin/env python3
"""
Position cards and section headers on an App Studio page (60-column grid; compact 12).

    python3 apply_layout.py <pageId> <cards.json> <layout_spec.json>

cards.json:       {"key": <cardId>, ...}
layout_spec.json: {"rows": [[["key", x, y, w, h, "kind"], ...], ...]}
  kind = filter | tile | chart | table | header   (header key = "HEADER:Section title")

Cards on the page but absent from the spec go to the appendix. Re-runnable.
"""
import copy, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from domo_api import req, j

FLAGS = {"filter": dict(hideTitle=True,  hideSummary=True,  hideBorder=True,  hideMargins=True,  fitToFrame=True),
         "tile":   dict(hideTitle=False, hideSummary=False, hideBorder=False, hideMargins=False, fitToFrame=False),
         "chart":  dict(hideTitle=False, hideSummary=True,  hideBorder=False, hideMargins=False, fitToFrame=False),
         "table":  dict(hideTitle=False, hideSummary=True,  hideBorder=False, hideMargins=False, fitToFrame=False)}
COMPACT_H = {"filter": 3, "tile": 5, "chart": 12, "table": 14}
BASE = {"compactInteractionDefault": True, "hideDescription": True, "summaryNumberOnly": False, "hideTimeframe": False, "hideFooter": False,
        "hideWrench": False, "hasSummary": False, "acceptFilters": True, "acceptDateFilter": True, "acceptSegments": True}

def apply(page_id, cards, rows):
    st, out = req("GET", f"/api/content/v4/pages/{page_id}/layouts"); layout = j(out); assert st == 200, out
    by_card = {c["cardId"]: c for c in layout["content"] if c["type"] == "CARD"}
    next_key = max([c["contentKey"] for c in layout["content"]] + [0]) + 100
    content, std, cmp = [], [], []
    for e in layout["standard"]["template"]:
        if e.get("contentKey") == 0: std.append(e)
    for e in layout["compact"]["template"]:
        if e.get("contentKey") == 0: cmp.append(e)
    cy = 0; placed = set()
    for row in rows:
        for key, x, y, w, h, kind in row:
            if kind == "header":
                ck = next_key; next_key += 1
                content.append({**BASE, "contentKey": ck, "type": "HEADER", "text": key.split(":", 1)[1], "hideTitle": False, "hideSummary": False,
                                "hideMargins": False, "fitToFrame": False, "hideBorder": False, "virtual": False, "virtualAppendix": False})
                std.append({"contentKey": ck, "type": "HEADER", "x": x, "y": y, "width": w, "height": h, "virtual": False, "virtualAppendix": False, "children": None})
                cmp.append({"contentKey": ck, "type": "HEADER", "x": 0, "y": cy, "width": 12, "height": 3, "virtual": False, "virtualAppendix": False, "children": None}); cy += 3
                continue
            cid = cards.get(key)
            if cid is None or cid not in by_card: print("not on page, skipping:", key); continue
            e = copy.deepcopy(by_card[cid]); e.update(FLAGS[kind]); e.update({"virtual": False, "virtualAppendix": False}); content.append(e); placed.add(cid)
            std.append({**FLAGS[kind], "contentKey": e["contentKey"], "type": "CARD", "x": x, "y": y, "width": w, "height": h, "virtual": False, "virtualAppendix": False, "style": None, "children": None})
            cmp.append({**FLAGS[kind], "contentKey": e["contentKey"], "type": "CARD", "x": 0, "y": cy, "width": 12, "height": COMPACT_H[kind], "virtual": False, "virtualAppendix": False, "style": None, "children": None}); cy += COMPACT_H[kind]
    for c in layout["content"]:                                             # leftovers -> appendix
        if c["type"] == "CARD" and c["cardId"] in placed: continue
        if c["type"] == "HEADER": continue                                   # headers are rebuilt from the spec every run
        e = copy.deepcopy(c); e.update({"virtual": True, "virtualAppendix": True}); content.append(e)
        std.append({"contentKey": c["contentKey"], "type": c["type"], "x": 0, "y": 0, "width": 15, "height": 14, "virtual": True, "virtualAppendix": True, "style": None, "children": None})
        cmp.append({"contentKey": c["contentKey"], "type": c["type"], "x": 0, "y": 0, "width": 6, "height": 14, "virtual": True, "virtualAppendix": True, "style": None, "children": None})
    layout.update({"content": content, "isDynamic": False}); layout["standard"]["template"] = std; layout["compact"]["template"] = cmp
    lock = f"/api/content/v4/pages/layouts/{layout['layoutId']}/writelock"
    st, out = req("PUT", lock, {}); assert st < 300, f"writelock: {out}"
    st, out = req("PUT", f"/api/content/v4/pages/layouts/{layout['layoutId']}", layout); print("PUT layout ->", st, out[:200] if st >= 300 else "")
    req("DELETE", lock)
    print(f"placed {len(placed)} cards, {sum(1 for c in content if c['type']=='HEADER')} headers")

if __name__ == "__main__":
    page_id, cards_path, spec_path = sys.argv[1], sys.argv[2], sys.argv[3]
    apply(page_id, json.load(open(cards_path)), json.load(open(spec_path))["rows"])
