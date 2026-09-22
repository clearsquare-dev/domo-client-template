#!/usr/bin/env python3
"""
Create an API dataset from a CSV and load it.

  python3 create_dataset.py data.csv "Dataset Name" [--desc "..."] [--types "Col A=DATE,Qty=LONG"]

Types default to STRING; pass --types for DATE / DATETIME / LONG / DOUBLE / DECIMAL columns, or
let --infer sniff the first 200 rows. Prints the dataset ID and commit summary.
"""
import argparse, csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from domo_api import req, j

def infer(rows, idx):
    vals = [r[idx] for r in rows if idx < len(r) and r[idx] != ""]
    if not vals: return "STRING"
    if all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) for v in vals): return "DATE"
    if all(re.fullmatch(r"-?\d+", v) for v in vals): return "LONG"
    if all(re.fullmatch(r"-?\d+(\.\d+)?", v) for v in vals): return "DOUBLE"
    return "STRING"

ap = argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("name"); ap.add_argument("--desc", default="")
ap.add_argument("--types", default=""); ap.add_argument("--infer", action="store_true"); ap.add_argument("--parts", type=int, default=2)
a = ap.parse_args()
with open(a.csv, newline="") as f:
    rd = csv.reader(f); header = next(rd); sample = [r for _, r in zip(range(200), rd)]
types = {k.strip(): v.strip().upper() for k, v in (p.split("=") for p in a.types.split(",") if p)}
cols = [{"name": h, "type": types.get(h, infer(sample, i) if a.infer else "STRING")} for i, h in enumerate(header)]
print("schema:", [(c["name"], c["type"]) for c in cols])

st, out = req("POST", "/api/data/v2/datasources", {"dataSourceName": a.name, "description": a.desc, "dataProviderType": "api", "schema": {"columns": cols}})
assert st < 300, out; ds = j(out)["dataSource"]["dataSourceId"]; print("DATASET_ID", ds)

body = open(a.csv, "rb").read().split(b"\n", 1)[1]                      # positional CSV, no header
st, out = req("POST", f"/api/data/v3/datasources/{ds}/uploads", {"action": "REPLACE", "message": "initial load", "appendId": None})
assert st < 300, out; uid = j(out)["uploadId"]
n = max(1, a.parts); size = len(body) // n; pos = 0
for i in range(1, n + 1):
    end = len(body) if i == n else body.find(b"\n", pos + size) + 1
    st, out = req("PUT", f"/api/data/v3/datasources/{ds}/uploads/{uid}/parts/{i}", ctype="text/csv", raw=body[pos:end]); assert st < 300, out; pos = end
st, out = req("PUT", f"/api/data/v3/datasources/{ds}/uploads/{uid}/commit", {"index": True, "action": "REPLACE", "message": "initial load"})
print("commit ->", st, out[:300])
