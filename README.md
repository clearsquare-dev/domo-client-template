# Domo Client Template

A starter workspace for Domo client engagements driven with **Claude Code**. Click **Use this template**, set two environment variables, and you have a ready-to-go project with Domo skills, auth conventions, and operating rules already wired up — no separate skill install, no Python virtualenv to provision.

Built for Clearsquare's Domo implementation work; self-contained so any teammate gets the full setup just by cloning.

## What's inside

| Path | Purpose |
| :--- | :--- |
| `CLAUDE.md` | The operating guide Claude Code reads — safety posture, auth, API rules, endpoints. Customize the **Context for this Project** block per client. |
| `SETUP.md` | Step-by-step checklist for standing up a new client workspace. |
| `.env.example` | Template for the two required vars (`DOMO_INSTANCE`, `DOMO_ACCESS_TOKEN`). Copy to `.env`. |
| `.claude/skills/` | Four bundled Domo skills, auto-discovered by Claude Code on clone. |
| `manual/` | Main workspace for analysis and data engineering, organized by data source. |
| `apps/` | Domo Custom Apps (vanilla JS + HTML + CSS + Tailwind CDN). |
| `qa/` | Quality-assurance scripts and one-offs. |

### Bundled skills

| Skill | What it does |
| :--- | :--- |
| `domo-get-dataset-schema` | Retrieve a dataset's column schema by name or ID. |
| `domo-query-dataset` | Query column values from a dataset, with optional filters. |
| `domo-dataflow` | Read and modify Magic ETL dataflows. |
| `domo-apps` | Build and deploy Domo Custom Apps. |

## For coworkers: how to use this template

**Do not `git clone` this template directly to do client work.** A direct clone keeps this template's history and points `origin` back here — client commits would target the template. Instead, generate a fresh, independent repo per client:

- **Web:** On this repo's page, click **Use this template → Create a new repository**, name it for the client (e.g. `domo-acme`), set it **private**, and create. Then clone *that* new repo.
- **CLI:**
  ```bash
  gh repo create clearsquare-dev/domo-acme --template clearsquare-dev/domo-client-template --private --clone
  cd domo-acme
  ```

This gives a clean repo with the client as `origin` and no link back to the template. (Cloning this template directly is only for reading it or improving the template itself.)

## Quick start

1. Use the template to create a client repo (see above).
2. Configure credentials:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` — set `DOMO_INSTANCE` (e.g. `acme.domo.com`) and `DOMO_ACCESS_TOKEN` (generate in Domo: **Admin > Authentication > Access Tokens**).
3. Verify connectivity:
   ```bash
   if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
   curl -s -o /dev/null -w "%{http_code}\n" \
     "https://$DOMO_INSTANCE/api/content/v2/users/me" \
     -H "X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
   # Expect: 200
   ```
4. Fill in the **Context for this Project** section at the bottom of `CLAUDE.md`.

Full details in [`SETUP.md`](SETUP.md).

## Authentication model

The default path uses a long-lived **developer access token** (`DOMO_ACCESS_TOKEN`) sent as the `X-DOMO-Developer-Token` header. No session exchange, no JSON parsing, no Python or `jq` required — it works across `/api/data`, `/api/dataprocessing`, and `/api/query`. A SID-based session flow is documented in `CLAUDE.md` as a fallback for instances not yet migrated to a token.

## Safety posture

`CLAUDE.md` instructs Claude to operate **read-only by default**. Write operations (`POST`/`PUT`/`PATCH`/`DELETE`) require an explicit request and a pre-flight summary of the intended change. See the **Safety & Write Permissions** section of `CLAUDE.md`.

## Notes

- `.env`, `.venv/`, `.domo_cli/`, and `.idea/` are gitignored — secrets and machine-specific files never get committed.
- No Python environment ships with the template. If a one-off script needs Python, create your own (gitignored) virtualenv.
- The bundled skills are point-in-time copies. If the canonical skills are updated, refresh the copies here.
