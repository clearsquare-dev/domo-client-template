#!/usr/bin/env python3
"""
Minimal Domo internal-API helper (developer token). Import from build scripts:

    import sys; sys.path.insert(0, ".claude/skills/domo-app-studio-build/scripts")
    from domo_api import req, j, INST, create_app, rename_page, card_data, card_definition, delete_card

Reads DOMO_INSTANCE / DOMO_ACCESS_TOKEN from ./.env (or the environment). Every call returns
(status_code, response_text); j() parses JSON when possible.
"""
import json, os, urllib.request, urllib.error

def _load_env():
    if os.path.exists(".env"):
        for line in open(".env"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
_load_env()
INST = os.environ["DOMO_INSTANCE"]; TOK = os.environ["DOMO_ACCESS_TOKEN"]

def req(method, path, body=None, ctype="application/json", raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(f"https://{INST}{path}", data=data, method=method,
        headers={"X-DOMO-Developer-Token": TOK, "Content-Type": ctype, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(r) as resp: return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()

def j(text):
    try: return json.loads(text)
    except Exception: return text

# ---- App Studio -------------------------------------------------------------
def create_app(title, description=""):
    """Returns (dataAppId, landingViewId). The landing view is the first page."""
    st, out = req("POST", "/api/content/v1/dataapps", {"title": title, "description": description,
                  "showNavigation": True, "showTitle": True, "navOrientation": "TOP"})
    assert st < 300, out; d = j(out); return d["dataAppId"], d["landingViewId"]

def rename_page(page_id, title):
    st, out = req("PUT", f"/api/content/v1/pages/{page_id}", {"pageId": page_id, "title": title, "pageName": title})
    assert st < 300, out

def set_pages_visible(app_id):
    st, out = req("GET", f"/api/content/v1/dataapps/{app_id}?includeHiddenViews=true"); app = j(out)
    for v in app["views"]: v["visible"] = True
    st, out = req("PUT", f"/api/content/v1/dataapps/{app_id}", app); assert st < 300, out

# ---- Cards ------------------------------------------------------------------
def create_card(body, page_id):
    st, out = req("PUT", f"/api/content/v3/cards/kpi?pageId={page_id}", body); return st, j(out)

def update_card(card_id, body):
    st, out = req("PUT", f"/api/content/v3/cards/kpi/{card_id}", body); return st, j(out)

def delete_card(card_id):
    return req("DELETE", f"/api/content/v1/cards/{card_id}")[0]

def card_definition(card_id):
    st, out = req("PUT", "/api/content/v3/cards/kpi/definition", {"urn": str(card_id)}); return j(out)

def card_data(card_id):
    """Rendered rows: {'aliases','mappings','rows','numRows'}."""
    st, out = req("POST", f"/api/content/v1/cards/{card_id}/data", {}); d = j(out)
    return (d.get("data") or {}) if isinstance(d, dict) else {}

def card_image(card_id, path, width=640, height=420):
    """Save a PNG of a chart card (tables render blank). Returns bytes written."""
    import base64
    st, out = req("PUT", f"/api/content/v1/cards/kpi/{card_id}/render?parts=image",
                  {"chartState": {"overrides": {}}, "scale": 1, "height": height, "width": width})
    b64 = (j(out).get("image") or {}).get("data", "") if st < 300 else ""
    if b64.startswith("data:"): b64 = b64.split(",", 1)[1]
    data = base64.b64decode(b64) if b64 else b""; open(path, "wb").write(data); return len(data)
