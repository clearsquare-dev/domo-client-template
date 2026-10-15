#!/usr/bin/env python3
"""Domo Code Engine + Workflows over plain REST (developer token, no MCP).

Reads DOMO_INSTANCE and DOMO_ACCESS_TOKEN from the environment or ./.env.
Every endpoint here was verified on 2026-10-15 (see ../SKILL.md).

  ce-create   --name N --code F --manifest F [--description D]   new package, version 1.0.0
  ce-version  --package P --version V --code F --manifest F       add a version with code
  ce-get      --package P [--version V]                           show versions / code + functions
  ce-run      --package P --version V --function FN [--inputs JSON]
  ce-release  --package P --version V                             IRREVERSIBLE
  wf-create   --name N [--description D] [--version V]            model + first version
  wf-save     --model M --version V --definition F                F holds designElements + dataList
  wf-validate --model M --version V                               validates the SAVED definition
  wf-test     --model M --version V [--inputs JSON]               test run, waits for the result
  wf-deploy   --model M --version V
  wf-undeploy --model M --version V
  wf-delete   --model M                                           undeploys, then deletes
  ce-delete   --package P                                         deletes every version (incl. released)
  wf-get      --model M [--version V]
  wf-runs     --model M [--limit N]
  query       --dataset D --sql "SELECT ... FROM table"
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_env():
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    missing = [k for k in ("DOMO_INSTANCE", "DOMO_ACCESS_TOKEN") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing {', '.join(missing)} (set them in .env or the environment)")


def call(method, path, body=None):
    url = f"https://{os.environ['DOMO_INSTANCE']}/{path.lstrip('/')}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-DOMO-Developer-Token": os.environ["DOMO_ACCESS_TOKEN"],
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as err:
        sys.exit(f"{method} {path} -> HTTP {err.code}: {err.read().decode()[:1000]}")
    return json.loads(raw) if raw.strip() else None


def show(obj):
    print(json.dumps(obj, indent=2))


def read_json(path):
    return json.loads(Path(path).read_text())


def manifest_functions(path):
    data = read_json(path)
    return data["functions"] if isinstance(data, dict) else data


# --- Code Engine -------------------------------------------------------------

CE = "api/codeengine/v2/packages"


def package_body(args):
    return {
        "name": args.name,
        "description": args.description or "",
        "code": Path(args.code).read_text(),
        "environment": "LAMBDA",
        "language": "JAVASCRIPT",
        "manifest": {"functions": manifest_functions(args.manifest), "configuration": {"accountsMapping": []}},
    }


def ce_create(args):
    pkg = call("POST", CE, package_body(args))
    print(f"package {pkg['id']} version {pkg['versions'][0]['version']}")
    ce_check(pkg["id"], pkg["versions"][0]["version"], args.manifest)


def ce_version(args):
    pkg = call("GET", f"{CE}/{args.package}")
    args.name, args.description = pkg["name"], pkg.get("description")
    body = package_body(args)
    body.update(id=args.package, version=args.version)
    call("POST", CE, body)
    print(f"package {args.package} version {args.version}")
    ce_check(args.package, args.version, args.manifest)


def ce_check(package, version, manifest):
    """Confirm the stored code and list flags match what was sent."""
    stored = call("GET", f"{CE}/{package}/versions/{version}?parts=functions,code")
    wanted = {(f["name"], i["name"]): i["isList"] for f in manifest_functions(manifest) for i in f["inputs"]}
    got = {(f["name"], i["name"]): i["isList"] for f in stored["functions"] for i in f["inputs"]}
    if wanted != got:
        sys.exit(f"Function manifest mismatch.\n wanted {wanted}\n stored {got}")
    print(f"verified: {len(stored['code'] or '')} chars of code, {len(stored['functions'])} function(s), list flags match")


def ce_get(args):
    if args.version:
        show(call("GET", f"{CE}/{args.package}/versions/{args.version}?parts=functions,code"))
    else:
        for v in call("GET", f"{CE}/{args.package}/versions"):
            print(v["version"], "released" if v.get("releasedOn") or v.get("released") else "draft")


def ce_run(args):
    inputs = json.loads(args.inputs or "{}")
    result = call("POST", f"{CE}/{args.package}/versions/{args.version}/functions/{args.function}",
                  {"inputVariables": inputs})
    show({k: result.get(k) for k in ("status", "result", "stderr", "errorInformation")})
    if result.get("status") != "SUCCESS":
        sys.exit(1)


def ce_release(args):
    result = call("POST", f"{CE}/{args.package}/versions/{args.version}/release")
    print(f"released {args.package} {result['version']} at {result['releasedOn']}")


# --- Workflows ---------------------------------------------------------------

WF1, WF2 = "api/workflow/v1/models", "api/workflow/v2"


def wf_create(args):
    model = call("POST", WF1, {"name": args.name, "description": args.description or ""})
    call("POST", f"{WF1}/{model['id']}/versions", {"version": args.version})
    print(f"model {model['id']} version {args.version}")


def wf_save(args):
    source = read_json(args.definition)
    definition = {"designElements": source["designElements"], "dataList": source["dataList"], "version": 2}
    call("PUT", f"{WF1}/{args.model}/versions/{args.version}", {"savedJson": json.dumps(definition)})
    saved = json.loads(call("GET", f"{WF1}/{args.model}/versions/{args.version}")["savedJson"])
    sent, kept = len(definition["designElements"]), len(saved["designElements"])
    print(f"saved {kept}/{sent} design elements")
    if kept != sent:
        sys.exit("Some elements were dropped: check their `type` values")


def wf_validate(args):
    issues = call("POST", f"{WF1}/{args.model}/versions/{args.version}/validate", {}) or []
    for issue in issues:
        print(issue["message"]["validationLevel"], issue["message"]["id"], issue.get("name") or "", issue.get("params") or "")
    errors = [i for i in issues if i["message"]["validationLevel"] == "ERROR"]
    print(f"{len(errors)} error(s), {len(issues) - len(errors)} other")
    if errors:
        sys.exit(1)


def wf_test(args):
    run = call("POST", f"{WF2}/models/{args.model}/versions/{args.version}/test", json.loads(args.inputs or "{}"))
    print(f"execution {run['id']}")
    while run["status"] in ("IN_PROGRESS", "RUNNING", "NOT_STARTED"):
        time.sleep(3)
        run = call("GET", f"{WF2}/executions/{run['id']}")
    print(f"status {run['status']}")
    if run["status"] != "COMPLETED":
        show(call("GET", f"{WF2}/executions/{run['id']}/events"))
        sys.exit(1)


def wf_deploy(args):
    result = call("POST", f"{WF2}/models/{args.model}/versions/{args.version}/release", {})
    print(f"deployed {args.model} {args.version}; manual trigger {result.get('manualTriggerId')}")


def wf_undeploy(args):
    call("PUT", f"{WF1}/{args.model}/versions/{args.version}/deployment", {"active": False})
    print(f"deactivated {args.model} {args.version}")


def wf_delete(args):
    model = call("GET", f"{WF1}/{args.model}")
    for v in model["versions"]:
        if v.get("active"):
            call("PUT", f"{WF1}/{args.model}/versions/{v['version']}/deployment", {"active": False})
    call("DELETE", f"{WF1}/{args.model}")
    print(f"deleted workflow {args.model} ({model['name']})")


def ce_delete(args):
    """Deleting the last version removes the package; released versions can be deleted too."""
    for v in call("GET", f"{CE}/{args.package}/versions"):
        call("DELETE", f"{CE}/{args.package}/versions/{v['version']}")
    print(f"deleted package {args.package}")


def wf_get(args):
    if args.version:
        version = call("GET", f"{WF1}/{args.model}/versions/{args.version}")
        version["savedJson"] = json.loads(version["savedJson"])
        show(version)
    else:
        model = call("GET", f"{WF1}/{args.model}")
        for v in model["versions"]:
            print(v["version"], "deployed" if v.get("active") else "draft", v.get("deployedOn") or "")


def wf_runs(args):
    for run in call("GET", f"{WF2}/executions?modelId={args.model}")[: args.limit]:
        print(run["startedAt"], run["status"], run["triggerType"], run.get("triggerName") or "", run["id"])


def query(args):
    result = call("POST", f"api/query/v1/execute/{args.dataset}", {"sql": args.sql})
    print("\t".join(result["columns"]))
    for row in result["rows"]:
        print("\t".join("" if v is None else str(v) for v in row))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    spec = {
        "ce-create": (ce_create, ["name", "code", "manifest", "?description"]),
        "ce-version": (ce_version, ["package", "version", "code", "manifest"]),
        "ce-get": (ce_get, ["package", "?version"]),
        "ce-run": (ce_run, ["package", "version", "function", "?inputs"]),
        "ce-release": (ce_release, ["package", "version"]),
        "wf-create": (wf_create, ["name", "?description", "?version=1.0.0"]),
        "wf-save": (wf_save, ["model", "version", "definition"]),
        "wf-validate": (wf_validate, ["model", "version"]),
        "wf-test": (wf_test, ["model", "version", "?inputs"]),
        "wf-deploy": (wf_deploy, ["model", "version"]),
        "wf-undeploy": (wf_undeploy, ["model", "version"]),
        "wf-delete": (wf_delete, ["model"]),
        "ce-delete": (ce_delete, ["package"]),
        "wf-get": (wf_get, ["model", "?version"]),
        "wf-runs": (wf_runs, ["model", "?limit=10"]),
        "query": (query, ["dataset", "sql"]),
    }
    for name, (func, options) in spec.items():
        p = sub.add_parser(name)
        p.set_defaults(func=func)
        for opt in options:
            optional = opt.startswith("?")
            opt, _, default = opt.lstrip("?").partition("=")
            kwargs = {"required": not optional, "default": default or None}
            if opt == "limit":
                kwargs.update(type=int, default=int(default))
            p.add_argument(f"--{opt}", **kwargs)
    args = parser.parse_args()
    load_env()
    args.func(args)


if __name__ == "__main__":
    main()
