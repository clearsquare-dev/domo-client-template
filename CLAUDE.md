# CLAUDE.md — Domo API & Client Environment Guide

This file defines the operational constraints and technical patterns for
interacting with a client's Domo instance via Claude Code and the Domo CLI.

> **Template note:** This is a generic Domo client template. Fill in the
> **Context for this Project** section at the bottom, copy `.env.example` to
> `.env`, and follow `SETUP.md`.

## ⚠️ CRITICAL: Safety & Write Permissions

- **Read-Only Default:** Assume a "read-only" posture. Do **NOT** perform any
  `POST`, `PUT`, `PATCH`, or `DELETE` operations unless explicitly instructed by
  the user for a specific task.
- **Pre-Write Briefing:** Before executing any write operation, you must provide
  a concise summary of:
  1. What specific data or configuration is being changed.
  2. The target Dataset or Dataflow ID.
  3. The potential impact (e.g., "This will overwrite the entire Dataflow
     definition").
- **Verification:** Always perform a `GET` on a resource immediately before a
  `PUT` to ensure the payload is based on the most current state of the instance.

## 🛡️ Security & Environment

- **Local Credentials:** Any Domo CLI sessions are isolated to `./.domo_cli`. If
  this is not yet created and you need the CLI fallback, create it.
- **Environment Variables:** Instance settings are pulled from the local `.env`
  file.
- **Write Safety:** NEVER perform write operations (POST/PUT/DELETE) without an
  explicit request and a "pre-flight" summary of the intended change.

## 📁 Project Structure & Navigation

- **Root**: Contains core config (`.env`, `CLAUDE.md`) and, if used, the local
  `.domo_cli` session.
- **`manual/`**: The primary workspace containing source-specific logic.
  - `manual/[source_name]/`: Subdirectories organized by data source.
  - **Reference Logic**: Look here first to see how previous tasks were handled.
- **`apps/`**: Domo Custom Apps (vanilla JS + HTML + CSS + Tailwind CDN).
- **`qa/`**: Quality Assurance — one-off files and scripts for QA work.

> **No bundled Python environment.** This template ships no `.venv`. If a one-off
> script needs Python, create your own virtual environment locally — it is
> gitignored. The primary auth path below needs no Python at all.

### 🗺️ Project Map (High-Level)

```text
.
├── .claude/skills/     # Bundled Domo skills (auto-discovered on clone)
├── .domo_cli/          # Isolated Domo CLI credentials, if used [gitignored]
├── manual/             # Main workspace for analysis and data engineering
├── apps/               # Domo Custom Apps
├── qa/                 # Quality Assurance (mostly one-off)
├── .env                # Instance-specific variables [gitignored]
└── CLAUDE.md           # This file
```

## 🛠 Authentication

**Primary method (preferred — no JSON parsing required).** If
`DOMO_ACCESS_TOKEN` is set in `.env`, use it directly. No session exchange, no
Python, no `jq`:

```bash
# Load instance + token from .env
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi

# Use this header on every request:
AUTH_HEADER="X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
```

This token is long-lived (generated via **Admin > Authentication > Access
Tokens**) and works across `/api/data`, `/api/dataprocessing`, and `/api/query`
endpoints in place of a SID. This is the default path for this template.

Quick connectivity check:

```bash
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://$DOMO_INSTANCE/api/content/v2/users/me" \
  -H "X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
# Expect: 200
```

---

### Fallback: Domo CLI / SID session (when no developer token)

Use this when `DOMO_ACCESS_TOKEN` is not set — e.g. an instance where you can
only sign in interactively and cannot mint an access token. This path reaches the
**same internal endpoints** as the developer token, so every skill (including
`domo-dataflow`) works at full capability. It parses JSON, so it uses `python3`
(preinstalled on macOS and most Linux).

> **Prerequisite — a one-time human login the agent CANNOT perform.**
> `domo login` is an interactive browser flow. A human must run it once, scoped
> to the project jail, after installing the Domo CLI:
>
> ```bash
> export XDG_CONFIG_HOME="$PWD/.domo_cli" && domo login -i <instance>.domo.com
> ```
>
> This writes `./.domo_cli/configstore/ryuu/<instance>.domo.com.json` containing a
> long-lived `refreshToken`.

**Agent rules for this path:**

1. **Check for the session file first.** If
   `./.domo_cli/configstore/ryuu/$DOMO_INSTANCE.json` does not exist, **STOP and
   ask the human to run the login command above.** Never attempt to automate the
   browser login.
2. **If the session exists, derive a SID autonomously** with the snippet below.
3. **Header:** send the SID as `X-Domo-Authentication: $SID` against the internal
   `https://$DOMO_INSTANCE/api/...` endpoints (the ones every skill uses).
4. **Lifetime:** the SID expires after ~1 hour. On a `401`, **re-run the exchange
   below — do NOT re-login.** The `refreshToken` is long-lived. Only ask the human
   to re-login if the refresh token itself is rejected.

```bash
# 1. Load instance from .env
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi

# 2. Local session path (the "jail")
LOCAL_CONFIG="./.domo_cli/configstore/ryuu/$DOMO_INSTANCE.json"

if [ -f "$LOCAL_CONFIG" ]; then
  # 3. refresh_token -> access_token -> SID
  REFRESH_TOKEN=$(python3 -c "import json; print(json.load(open('$LOCAL_CONFIG'))['refreshToken'])")

  ACCESS_TOKEN=$(curl -s -X POST "https://$DOMO_INSTANCE/api/oauth2/token" \
    -H "content-type: application/x-www-form-urlencoded" \
    -d "client_id=domo:internal:devstudio&grant_type=refresh_token&refresh_token=$REFRESH_TOKEN" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")

  SID=$(curl -s "https://$DOMO_INSTANCE/api/oauth2/sid" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['sid'])")

  # Use SID in header: "X-Domo-Authentication: $SID"
else
  echo "No local session. A human must run:"
  echo "  export XDG_CONFIG_HOME=\"\$PWD/.domo_cli\" && domo login -i $DOMO_INSTANCE"
fi
```

## 📐 API Implementation Rules

- **Querying:** Use the SQL endpoint `/api/query/v1/execute/{datasetId}`. Always
  use `table` as the table name in your SQL string to refer to the dataset.
- **Pagination:** Dataset lists are capped at 50 per page. Use `limit` and
  `offset` for large inventories.
- **Dataflows:**
  - Do **NOT** use `?hydrate=full` on the dataflows endpoint (known 400 errors).
  - When updating, `PUT` replaces the **entire** JSON definition. Never partial.
- **Tooling:** Use `curl` for all requests.

## 🧰 Skills

Use the `Skill` tool to invoke these before taking action:

| Task                                   | Skill                     |
| :------------------------------------- | :------------------------ |
| **Get dataset schema** (by name or ID) | `domo-get-dataset-schema` |
| **Query column values from a dataset** | `domo-query-dataset`      |
| **Read / modify a Magic ETL dataflow** | `domo-dataflow`           |
| **Build / modify a Domo Custom App**   | `domo-apps`               |

## 📖 Common Endpoints Reference

| Action                   | Method | Endpoint                                           |
| :----------------------- | :----- | :------------------------------------------------- |
| **Query Dataset (SQL)**  | POST   | `/api/query/v1/execute/{datasetId}`                |
| **Get Dataset Metadata** | GET    | `/api/data/v3/datasources/{datasetId}`             |
| **List Dataflows**       | GET    | `/api/dataprocessing/v1/dataflows`                 |
| **Get Dataflow Def**     | GET    | `/api/dataprocessing/v1/dataflows/{id}`            |
| **Update Dataflow**      | PUT    | `/api/dataprocessing/v1/dataflows/{id}`            |
| **Execute Dataflow**     | POST   | `/api/dataprocessing/v1/dataflows/{id}/executions` |

## Context for this Project

<!-- FILL THIS IN PER CLIENT.
Describe: the client (company, size, industry, focus), the engagement goal
(e.g. replicating Looker/Tableau dashboards), primary data sources, and any
constraints or plan specifics the agent should know. -->

I work for Clearsquare, a Domo implementation partner. This project is for
**[CLIENT NAME]**, a **[industry / size]** company. The engagement goal is
**[goal]**. Primary data source(s): **[sources]**.
