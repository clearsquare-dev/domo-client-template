---
name: domo-workflow-rest
description: Build, test and deploy Domo Workflows and Code Engine packages using only a developer token (plain REST, no Domo MCP servers). Use when the instance has no odyssey_workflow_toolkit / code_engine_toolkit MCP server, or when exact Code Engine code must be uploaded verbatim. Covers creating packages with code, running and releasing functions, creating and saving workflow definitions, validating, test-running, deploying, undeploying and deleting.
---

# Domo Workflows + Code Engine over REST

All calls go through `scripts/domo_rest.py`, which needs only Python 3 and reads
`DOMO_INSTANCE` and `DOMO_ACCESS_TOKEN` from `./.env`. Run it from the project root:

```bash
python3 .claude/skills/domo-workflow-rest/scripts/domo_rest.py <command> --help
```

Every endpoint below was verified on 2026-10-15 against `clearsquare-co-partner` with a
developer token, using throwaway objects that were then deleted.

## Write safety

CLAUDE.md's write rules apply. Before running any create, save, run, test, release, deploy or
delete command, tell the user what will change and on which instance, and get explicit approval.
Two of these need their own separate confirmation:

- `ce-release` makes that version immutable.
- `wf-test` runs the real workflow logic against real datasets. It is not a dry run.

## Typical build

```bash
R=.claude/skills/domo-workflow-rest/scripts/domo_rest.py
python3 $R ce-create  --name "My Utils" --code code.js --manifest functions_manifest.json
python3 $R ce-run     --package <P> --version 1.0.0 --function myFn --inputs '{"x":1}'
python3 $R ce-release --package <P> --version 1.0.0          # confirm first
python3 $R wf-create  --name "My Workflow"                    # prints model id, version 1.0.0
python3 $R wf-save    --model <M> --version 1.0.0 --definition workflow.json
python3 $R wf-validate --model <M> --version 1.0.0
python3 $R wf-test    --model <M> --version 1.0.0             # confirm first
python3 $R wf-deploy  --model <M> --version 1.0.0             # confirm first
```

Then add any dataset or alert triggers in the Workflows UI (see **Not possible over REST**).

## Endpoint reference

| Action | Call | Notes |
| :-- | :-- | :-- |
| Create package (+ code) | `POST /api/codeengine/v2/packages` | Body `{name, description, code, environment:"LAMBDA", language:"JAVASCRIPT", manifest:{functions, configuration:{accountsMapping:[]}}}`. Code and `isList` flags are stored exactly as sent. |
| New package version | `POST /api/codeengine/v2/packages` | Same body plus `id` and `version`. |
| Read version | `GET …/packages/{id}/versions/{v}?parts=functions,code` | |
| Update manifest only | `PUT …/packages/{id}/versions/{v}` | Body `{"functions":[…]}`; `code` is rejected here. |
| Run function | `POST …/packages/{id}/versions/{v}/functions/{fn}` | Body `{"inputVariables":{…}}`. Inputs at top level → 400. Works on drafts. |
| Release version | `POST …/packages/{id}/versions/{v}/release` | Immutable afterwards. |
| Delete version | `DELETE …/packages/{id}/versions/{v}` | Works on released versions too; deleting the last one removes the package. |
| Create workflow | `POST /api/workflow/v1/models` `{name, description}` | `versions` in this body is ignored. |
| Add version | `POST /api/workflow/v1/models/{id}/versions` `{"version":"1.0.0"}` | |
| Save definition | `PUT /api/workflow/v1/models/{id}/versions/{v}` | Body `{"savedJson": "<JSON string of {designElements, dataList, version:2}>"}`. A raw DTO returns 200 but saves nothing. |
| Read definition | `GET /api/workflow/v1/models/{id}/versions/{v}` | `savedJson` is a string. |
| Validate | `POST …/models/{id}/versions/{v}/validate` | Validates the **saved** definition, not the request body. |
| Test run | `POST /api/workflow/v2/models/{id}/versions/{v}/test` | Body `{}` for no inputs. Passing start inputs this way is unverified. |
| Run status / events | `GET /api/workflow/v2/executions/{id}`, `…/{id}/events` | List: `GET /api/workflow/v2/executions?modelId=` |
| Deploy | `POST /api/workflow/v2/models/{id}/versions/{v}/release` | Creates Manual + MCP triggers; returns `startEventId`. |
| Undeploy | `PUT /api/workflow/v1/models/{id}/versions/{v}/deployment` `{"active":false}` | |
| Delete workflow | `DELETE /api/workflow/v1/models/{id}` | Undeploy first, or it returns 403. |
| Dataset SQL | `POST /api/query/v1/execute/{datasetId}` `{"sql":"… FROM table"}` | |

## Not possible over REST (use the UI)

**Dataset/alert triggers.** These are Domo Alerts (`/api/social/v4/alerts`) with a `WORKFLOW` action.
Creating the alert itself works: post the body without `filterGroups`. But attaching the workflow
action returns 400/500 for every payload tried, and `POST /api/workflow/v2/triggers` with
`type: ALERT` returns 403 ("requires service.internal"). Add these triggers in the Workflows UI after
deploying. Existing ones can be read with `GET /api/social/v4/alerts/{id}`.

## Code Engine code rules

- JavaScript calls Domo with `const codeengine = require('codeengine');` and
  `await codeengine.sendRequest(method, url, body, null, contentType)`. There is no `require('domo')`.
- Export every function in `module.exports = { … }`, under the same names as `manifest.functions[].name`.
- Manifest entries use the stored shape: `{name, displayName, description, inputs:[{name, displayName, type, value:null, nullable, isList, children:null, entitySubType:null}], output:{…}}`.
  `type` values are lowercase: `text`, `number`, `decimal`, `boolean`, `object`, `dataset`, `date`, `datetime`.
- `ce-create` and `ce-version` re-read the stored version and fail if the list flags differ from the manifest.
- Workflows can only call **released** versions (validation code ODY_051).

## Workflow definition reference

Easiest path: copy an existing definition (`wf-get --model M --version V` → `savedJson`) and edit it.
For a fresh one, `designElements` is a single flat array of nodes and edges, and every element's
`index` equals its array position:

- **Start:** `{"id":"startNode","type":"rootNode","position":{x,y},"data":{"title":"Start","_designNode":"rootNode","type":"Start","isFormStart":false,"formId":null,"input":[]}}`
- **Code Engine task:** `type:"serviceTaskNode"`. Its `data` has `taskType:"nebulaFunction"`,
  `metadata:{packageId, version, functionName, settings:{}}`, `selectedTaskTitle` (must be non-empty),
  and `input` / `output` arrays of `{id, paramName, displayName, dataType, isList, required, value, mappedTo, visible:true, children:[], flag:"input"|"output"}`.
  `paramName` must match the function's input names. Required inputs need a `value` or a `mappedTo`;
  outputs need a `mappedTo` that is a `dataList` variable id.
- **Dataset query:** `type:"DATASET_QUERY_TASK"`. Its `data` has `dataset` (paramName `dataset`, `value` = dataset UUID),
  `query` (paramName `query`, `value` = rich-text list
  `[{"type":"paragraph","children":[{"text":"SELECT","sql":true},{"text":" `Col` AS col FROM `Table_0`","sql":false}]}]`),
  and `result` (paramName `result`, `dataType:"object"`, `isList:true`, `mappedTo` = a `dataList` id, with one child per column).
  The table is always `` `Table_0` ``. Output column names must be alphanumeric or underscore, so alias anything else with `AS`.
- **End:** `{"id":"endNode","type":"endNode","data":{"title":"End","_designNode":"endNode","terminating":false}}`
- **Edge:** `{"id":"edge-a-b-1","type":"defaultEdge","source":"a","target":"b","data":{"sourcePosition":"bottom","targetPosition":"top","path":[[400,160],[400,240]]},"style":{"zIndex":3},"arrowHeadType":"arrow"}`
- **`dataList` variables:** `{id, paramName, dataType, isList, isOutput, children:[], showChildren:false, entitySubType:null, value:null}`.
  A query result's children use ids like `varRows.childName`.
- **IDs:** node, variable and input/output ids are letters, digits and underscores only, starting with a letter.
  Edge ids may contain hyphens. UUIDs are not valid ids.
- **Layout:** one column at `x=300`, `y = 100 + row*140`; edge path runs from the source's bottom-centre to the target's top-centre.
- **Dropped elements:** unknown `type` values are silently dropped. `wf-save` compares element counts and fails if any were dropped.

Worked example (if copied into the project): `manual/webform_tag_workflows/`, which has two workflows and one package, templated for any instance.
