# Domo Business-User Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `domo-client-template-business`, a sibling repo to `domo-client-template` that gives a non-technical Domo client user the same skill capability, but with a zero-terminal, conversational onboarding flow instead of git/CLI setup.

**Architecture:** Fork the current repo's tracked files (via `git archive`, which naturally excludes `.git` and gitignored files) into a new local repo with fresh history. Add one new skill (`domo-first-run-setup`) that Claude runs automatically via a CLAUDE.md trigger the first time a session starts without a configured `.env`. Rewrite `README.md`/`SETUP.md` for a non-technical reader and strip the CLI/SID fallback auth path from `CLAUDE.md`, since it requires a terminal login this audience won't perform.

**Tech Stack:** Markdown (CLAUDE.md, SKILL.md, README.md, SETUP.md), bash/curl (auth + verification snippets Claude runs on the user's behalf), git.

**Source repo:** `/Users/cristiancruz/Desktop/domo-client-template`
**Target repo:** `/Users/cristiancruz/Desktop/domo-client-template-business` (new, created in Task 1)

There's no code here in the traditional sense — this is a documentation/skill-authoring project. "Tests" below are manual verification steps (grep checks, dry-run bash simulations, and a scripted read-through of the flow) rather than an automated test suite, since none exists or is warranted for a template repo of markdown and shell snippets.

---

### Task 1: Scaffold the new repo with fresh history

**Files:**
- Create: `/Users/cristiancruz/Desktop/domo-client-template-business/` (entire tree, copied)

- [ ] **Step 1: Export the current repo's tracked files into a new directory**

```bash
mkdir -p /Users/cristiancruz/Desktop/domo-client-template-business
cd /Users/cristiancruz/Desktop/domo-client-template
git archive HEAD | tar -x -C /Users/cristiancruz/Desktop/domo-client-template-business
```

`git archive` only includes tracked files, so `.env`, `.domo_cli/`, `.venv/`, and `.git/` are excluded automatically — no manual cleanup needed.

- [ ] **Step 2: Verify the copy**

```bash
diff -rq --exclude=.git /Users/cristiancruz/Desktop/domo-client-template /Users/cristiancruz/Desktop/domo-client-template-business
```

Expected: no output (directories match, modulo `.git`).

- [ ] **Step 3: Initialize fresh git history**

```bash
cd /Users/cristiancruz/Desktop/domo-client-template-business
git init
git add -A
git commit -m "Initial import from domo-client-template"
```

Expected: commit succeeds, `git log --oneline` shows exactly one commit.

- [ ] **Step 4: Confirm no history leakage**

```bash
git -C /Users/cristiancruz/Desktop/domo-client-template-business log --oneline | wc -l
```

Expected: `1`.

---

### Task 2: Add the `domo-first-run-setup` skill

**Files:**
- Create: `/Users/cristiancruz/Desktop/domo-client-template-business/.claude/skills/domo-first-run-setup/SKILL.md`

- [ ] **Step 1: Write the skill file**

```markdown
---
name: domo-first-run-setup
description: Run at the start of any session in this workspace before addressing anything else, whenever .env is missing or missing DOMO_INSTANCE/DOMO_ACCESS_TOKEN values. Walks a non-technical user through connecting their Domo instance conversationally — no terminal or file editing required from them. Also re-invoke mid-session if a Domo API call returns 401.
---

# domo-first-run-setup

## Overview

This workspace is opened directly by a business user with no terminal or
git experience. There is no manual `SETUP.md` copy-paste step for them —
this skill is how `.env` gets created and filled in, entirely through
conversation.

## Step 1: Detect whether setup is needed

```bash
if [ ! -f .env ]; then
  echo "MISSING_ENV_FILE"
elif ! grep -q '^DOMO_INSTANCE=.\+' .env || ! grep -q '^DOMO_ACCESS_TOKEN=.\+' .env; then
  echo "INCOMPLETE_ENV_FILE"
else
  echo "CONFIGURED"
fi
```

If the output is `CONFIGURED`, stop here — skip the rest of this skill and
go straight to what the user actually asked for.

## Step 2: Create `.env` if it doesn't exist yet

```bash
[ -f .env ] || cp .env.example .env
```

## Step 3: Ask for their Domo instance

Ask in plain language, e.g.: "What's the web address you use to log into
Domo? It usually looks like `yourcompany.domo.com`."

Accept whatever they paste (with or without `https://`, with or without a
trailing slash) and normalize it to a bare hostname — e.g.
`https://acme.domo.com/` becomes `acme.domo.com` — before writing it to
`.env`.

## Step 4: Walk them through generating an access token

Explain, step by step, without assuming any prior knowledge:

1. "Log into Domo in your browser."
2. "Click your name or the gear icon in the top right, then go to **Admin**."
3. "Go to **Authentication > Access Tokens**."
4. "Click **Generate token**, give it a name like `Claude Assistant`, and
   create it."
5. "Domo will show you the token once — copy it and paste it here in the
   chat."

Note for the user: if they navigate away before copying it, Domo won't
show it again — they'll just need to generate a new one.

## Step 5: Write both values into `.env`

Use the Edit tool to set the `DOMO_INSTANCE` and `DOMO_ACCESS_TOKEN` lines
in `.env` to the values collected above, leaving the rest of the file
(comments, optional vars) untouched.

## Step 6: Verify connectivity

```bash
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://$DOMO_INSTANCE/api/content/v2/users/me" \
  -H "X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
```

- **200** → Tell the user they're connected, and suggest 2-3 example
  things they can ask for (e.g. "What datasets do we have?").
- **401** → Don't show the raw HTTP response. Say something like: "That
  didn't work — either the instance address or the token might be off.
  Can you double check the address, or generate a fresh token?" Then
  return to Step 3 or Step 4 depending on what they want to recheck, and
  re-run this step.
- **Anything else** (e.g. connection/DNS failure) → The instance address
  is most likely misspelled. Ask them to re-confirm it and retry.

Do not proceed to the user's original request until this returns 200.

## Step 7: Re-trigger on mid-session expiry

If any Domo API call later in the same session returns 401, don't try to
silently debug it or guess. Tell the user their connection appears to have
expired or been revoked, and re-run Steps 4-6 to collect a fresh token.

## Common Mistakes

- **Storing the instance with a scheme or trailing slash** — always
  normalize to a bare hostname (`acme.domo.com`, not
  `https://acme.domo.com/`) before writing `.env`, since other skills
  build URLs by prefixing `https://$DOMO_INSTANCE` directly.
- **Showing raw curl/HTTP errors to the user** — always translate a
  non-200 response into a plain-language next step (Step 6).
- **Re-running the whole skill on every message** — Step 1's detection
  check means this only engages when setup is actually incomplete.
```

- [ ] **Step 2: Verify the skill's frontmatter is well-formed**

```bash
head -4 /Users/cristiancruz/Desktop/domo-client-template-business/.claude/skills/domo-first-run-setup/SKILL.md
```

Expected: three lines of YAML frontmatter (`---`, `name:`, `description:`, `---`) matching the format of the existing skills in `.claude/skills/*/SKILL.md`.

- [ ] **Step 3: Commit**

```bash
cd /Users/cristiancruz/Desktop/domo-client-template-business
git add .claude/skills/domo-first-run-setup/SKILL.md
git commit -m "Add domo-first-run-setup skill for conversational onboarding"
```

---

### Task 3: Update CLAUDE.md for the business-user flow

**Files:**
- Modify: `/Users/cristiancruz/Desktop/domo-client-template-business/CLAUDE.md`

- [ ] **Step 1: Replace the template note and add the first-run trigger**

Old text (lines 6-8):

```markdown
> **Template note:** This is a generic Domo client template. Fill in the
> **Context for this Project** section at the bottom, copy `.env.example` to
> `.env`, and follow `SETUP.md`.
```

New text:

```markdown
> **Template note:** This is the business-user edition of Clearsquare's Domo
> client template. Before zipping and sending this to a client, fill in the
> **Context for this Project** section at the bottom. The person opening this
> workspace does not need to touch `.env` themselves — the
> `domo-first-run-setup` skill collects their Domo instance and access token
> conversationally the first time they chat.

## 🚦 First-Run Check — Read This Before Anything Else

At the start of every session, before addressing anything else the user
asks: check whether `.env` exists and has non-placeholder values for both
`DOMO_INSTANCE` and `DOMO_ACCESS_TOKEN`. If either is missing, invoke the
`domo-first-run-setup` skill first. Only proceed to the user's actual
request once that skill reports a successful connection (or reports the
workspace was already configured).
```

- [ ] **Step 2: Simplify the "Local Credentials" bullet**

Old text (line 26-27):

```markdown
- **Local Credentials:** Any Domo CLI sessions are isolated to `./.domo_cli`. If
  this is not yet created and you need the CLI fallback, create it.
```

New text:

```markdown
- **Local Credentials:** This template uses developer-token auth only (see
  **Authentication** below) — there is no local CLI session to manage.
```

- [ ] **Step 3: Reword the Authentication section intro (remove "fallback exists" framing)**

Old text (lines 62-64):

```markdown
**Primary method (preferred — no JSON parsing required).** If
`DOMO_ACCESS_TOKEN` is set in `.env`, use it directly. No session exchange, no
Python, no `jq`:
```

New text:

```markdown
This template uses a single authentication method: a long-lived developer
access token. Once `domo-first-run-setup` has run, `DOMO_ACCESS_TOKEN` will
be set in `.env` — use it directly. No session exchange, no Python, no `jq`:
```

- [ ] **Step 4: Delete the CLI/SID fallback section entirely**

Delete everything from the `---` divider through the end of the fallback
bash block (old lines 88-147), i.e. delete this whole block:

```markdown
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
```

The section immediately after this deletion, `## 📐 API Implementation Rules`, should now follow directly after the connectivity-check bash block from the Authentication section.

- [ ] **Step 5: Add `domo-first-run-setup` to the Skills table**

Old text (lines 164-169):

```markdown
| Task                                   | Skill                     |
| :------------------------------------- | :------------------------ |
| **Get dataset schema** (by name or ID) | `domo-get-dataset-schema` |
| **Query column values from a dataset** | `domo-query-dataset`      |
| **Read / modify a Magic ETL dataflow** | `domo-dataflow`           |
| **Build / modify a Domo Custom App**   | `domo-apps`               |
```

New text:

```markdown
| Task                                   | Skill                     |
| :------------------------------------- | :------------------------ |
| **First session / `.env` incomplete**  | `domo-first-run-setup`    |
| **Get dataset schema** (by name or ID) | `domo-get-dataset-schema` |
| **Query column values from a dataset** | `domo-query-dataset`      |
| **Read / modify a Magic ETL dataflow** | `domo-dataflow`           |
| **Build / modify a Domo Custom App**   | `domo-apps`               |
```

- [ ] **Step 6: Verify the fallback section is fully gone and the file is well-formed**

```bash
grep -n "domo login\|SID\|Fallback" /Users/cristiancruz/Desktop/domo-client-template-business/CLAUDE.md
```

Expected: no matches (the only remaining `SID`/`login` references were inside the deleted block).

```bash
grep "^## " /Users/cristiancruz/Desktop/domo-client-template-business/CLAUDE.md
```

Expected: 9 lines, in this exact order: First-Run Check, Safety & Write
Permissions, Security & Environment, Project Structure & Navigation,
Authentication, API Implementation Rules, Skills, Common Endpoints
Reference, Context for this Project.

- [ ] **Step 7: Commit**

```bash
cd /Users/cristiancruz/Desktop/domo-client-template-business
git add CLAUDE.md
git commit -m "Rework CLAUDE.md for zero-terminal business-user onboarding"
```

---

### Task 4: Rewrite SETUP.md for a non-technical reader

**Files:**
- Modify: `/Users/cristiancruz/Desktop/domo-client-template-business/SETUP.md` (full rewrite)

- [ ] **Step 1: Replace the entire file contents**

```markdown
# Getting Started

Welcome! This workspace connects Claude Code to your team's Domo instance
so you can ask questions about your data, pull reports, and even update
dashboards just by chatting — no SQL, no dashboard building by hand.

## 1. Install Claude Code Desktop

If you don't already have it installed, ask your Clearsquare contact for
the download link and install it like any other application.

## 2. Unzip and open this folder

Unzip the file Clearsquare sent you anywhere convenient (like your
Desktop). Open Claude Code Desktop, then open this unzipped folder as your
workspace.

## 3. Just start typing

Send any message — even just "hi". Claude will notice this is a new
workspace and walk you through connecting to your Domo instance: it'll ask
for your Domo web address, then guide you step by step through generating
an access code in Domo (a few clicks in your browser). Paste that back in,
and you're connected. You never need to open or edit any files yourself.

## 4. What you can ask

Once you're connected, try things like:

- "What datasets do we have?"
- "Show me the schema for the Sales dataset."
- "What were our top 5 regions by revenue last month?"
- "Look at the Customer Orders dataflow and tell me what it does."

## If something goes wrong

If Claude tells you your connection has expired or stopped working, just
say so — it will walk you through reconnecting the same way as the first
time.

## Questions?

Reach out to your Clearsquare contact — this workspace was set up
specifically for your team.
```

- [ ] **Step 2: Verify no leftover technical-audience instructions remain**

```bash
grep -in "git clone\|gh repo\|terminal\|cp .env" /Users/cristiancruz/Desktop/domo-client-template-business/SETUP.md
```

Expected: no matches.

- [ ] **Step 3: Commit**

```bash
cd /Users/cristiancruz/Desktop/domo-client-template-business
git add SETUP.md
git commit -m "Rewrite SETUP.md for non-technical business users"
```

---

### Task 5: Rewrite README.md

**Files:**
- Modify: `/Users/cristiancruz/Desktop/domo-client-template-business/README.md` (full rewrite)

- [ ] **Step 1: Replace the entire file contents**

```markdown
# Domo Client Template — Business User Edition

A ready-to-use Domo workspace for non-technical business users, driven
with **Claude Code**. Unlike Clearsquare's technical client template, this
version needs no git, no terminal commands, and no manual `.env` editing —
the person using it just opens the folder in Claude Code Desktop and
starts chatting. Setup happens conversationally on first use.

## What's inside

| Path | Purpose |
| :--- | :--- |
| `CLAUDE.md` | The operating guide Claude Code reads — safety posture, auth, API rules, endpoints. Customize the **Context for this Project** block per client before shipping. |
| `SETUP.md` | The walkthrough the business user reads (or Claude reads to them) when they first open this workspace. |
| `.env.example` | Template for the two required vars (`DOMO_INSTANCE`, `DOMO_ACCESS_TOKEN`). Filled in conversationally by the `domo-first-run-setup` skill — never edited by hand. |
| `.claude/skills/` | Five bundled Domo skills, auto-discovered by Claude Code on open. |
| `manual/` | Main workspace for analysis and data engineering, organized by data source. |
| `apps/` | Domo Custom Apps (vanilla JS + HTML + CSS + Tailwind CDN). |
| `qa/` | Quality-assurance scripts and one-offs. |

### Bundled skills

| Skill | What it does |
| :--- | :--- |
| `domo-first-run-setup` | Walks a new user through connecting their Domo instance conversationally, the first time they open the workspace (or after a token expires). |
| `domo-get-dataset-schema` | Retrieve a dataset's column schema by name or ID. |
| `domo-query-dataset` | Query column values from a dataset, with optional filters. |
| `domo-dataflow` | Read and modify Magic ETL dataflows. |
| `domo-apps` | Build and deploy Domo Custom Apps. |

## For Clearsquare: how to ship this to a client

This repo is maintained by Clearsquare, not cloned or forked by clients.
Per engagement:

1. Clone this repo fresh.
2. Fill in the **Context for this Project** section of `CLAUDE.md` for the
   client (name, industry, engagement goal, data sources).
3. Zip the folder, excluding `.git`.
4. Send the zip to the business user with a short note: install Claude
   Code Desktop, unzip, open the folder, and start chatting.

## Authentication model

This template supports developer-access-token auth only, collected
conversationally by `domo-first-run-setup` the first time a user opens the
workspace — there's no manual `.env` editing and no CLI/SID fallback path
(that path requires an interactive terminal login and doesn't fit a
zero-terminal audience; use the technical `domo-client-template` if an
engagement needs it).

## Safety posture

`CLAUDE.md` instructs Claude to operate **read-only by default**. Write
operations (`POST`/`PUT`/`PATCH`/`DELETE`) require an explicit request and
a pre-flight summary of the intended change. See the **Safety & Write
Permissions** section of `CLAUDE.md`.

## Notes

- `.env`, `.venv/`, `.domo_cli/`, and `.idea/` are gitignored — secrets and
  machine-specific files never get committed.
- No Python environment ships with the template.
- The bundled skills are point-in-time copies from `domo-client-template`.
  If the canonical skills are updated there, refresh the copies here.
```

- [ ] **Step 2: Verify no leftover "Use this template" / `gh repo create` instructions remain**

```bash
grep -in "use this template\|gh repo create\|git clone" /Users/cristiancruz/Desktop/domo-client-template-business/README.md
```

Expected: no matches.

- [ ] **Step 3: Commit**

```bash
cd /Users/cristiancruz/Desktop/domo-client-template-business
git add README.md
git commit -m "Rewrite README.md for the business-user template edition"
```

---

### Task 6: Manual verification of the full onboarding flow

No automated test suite applies here — this task is a scripted dry run
that simulates what `domo-first-run-setup` and the CLAUDE.md trigger will
actually do, using fake values, so a bug in the detection logic or the
verification curl is caught before this goes to a real client.

**Files:** none (verification only, run from `/Users/cristiancruz/Desktop/domo-client-template-business`)

- [ ] **Step 1: Simulate the "missing .env" case**

```bash
cd /Users/cristiancruz/Desktop/domo-client-template-business
rm -f .env
if [ ! -f .env ]; then
  echo "MISSING_ENV_FILE"
elif ! grep -q '^DOMO_INSTANCE=.\+' .env || ! grep -q '^DOMO_ACCESS_TOKEN=.\+' .env; then
  echo "INCOMPLETE_ENV_FILE"
else
  echo "CONFIGURED"
fi
```

Expected: `MISSING_ENV_FILE`.

- [ ] **Step 2: Simulate the "partially configured" case**

```bash
cp .env.example .env
if [ ! -f .env ]; then
  echo "MISSING_ENV_FILE"
elif ! grep -q '^DOMO_INSTANCE=.\+' .env || ! grep -q '^DOMO_ACCESS_TOKEN=.\+' .env; then
  echo "INCOMPLETE_ENV_FILE"
else
  echo "CONFIGURED"
fi
```

Expected: `INCOMPLETE_ENV_FILE` (`.env.example` ships with `DOMO_INSTANCE` set to a placeholder value and `DOMO_ACCESS_TOKEN` empty).

- [ ] **Step 3: Simulate the "fully configured" case**

```bash
printf 'DOMO_INSTANCE=fake-instance.domo.com\nDOMO_ACCESS_TOKEN=fake-token-value\n' > .env
if [ ! -f .env ]; then
  echo "MISSING_ENV_FILE"
elif ! grep -q '^DOMO_INSTANCE=.\+' .env || ! grep -q '^DOMO_ACCESS_TOKEN=.\+' .env; then
  echo "INCOMPLETE_ENV_FILE"
else
  echo "CONFIGURED"
fi
```

Expected: `CONFIGURED`.

- [ ] **Step 4: Simulate the connectivity check against a bad instance (expect graceful failure, not a crash)**

```bash
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://$DOMO_INSTANCE/api/content/v2/users/me" \
  -H "X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN" \
  --max-time 10
```

Expected: either a `4xx`/`5xx` status code or a curl error (fake instance
won't resolve) — confirms the check fails safely rather than hanging.
Per Step 6 of the skill, this maps to the "anything other than 200"
plain-language branch.

- [ ] **Step 5: Clean up the simulated `.env`**

```bash
cd /Users/cristiancruz/Desktop/domo-client-template-business
rm -f .env
```

`.env` is gitignored, so this just resets the local working tree to how a
freshly-unzipped copy would look — no `.env` present until a real user
goes through setup.

- [ ] **Step 6: Read through CLAUDE.md and SETUP.md end to end**

Open both files and confirm: (a) the First-Run Check section in
`CLAUDE.md` correctly names `domo-first-run-setup`, (b) `SETUP.md` never
tells the user to open or edit a file, run a terminal command, or use
git, and (c) the Skills table in `CLAUDE.md` lists all five skills
including the new one.

---

### Task 7: Final review and handoff note

**Files:** none

- [ ] **Step 1: Confirm the full commit history**

```bash
git -C /Users/cristiancruz/Desktop/domo-client-template-business log --oneline
```

Expected: 5 commits (initial import, skill, CLAUDE.md rework, SETUP.md rewrite, README.md rewrite).

- [ ] **Step 2: Confirm working tree is clean**

```bash
git -C /Users/cristiancruz/Desktop/domo-client-template-business status
```

Expected: `nothing to commit, working tree clean`.

- [ ] **Step 3: Stop — do not create or push to a GitHub remote automatically**

Creating a new GitHub repo and pushing is a shared/remote action outside
this plan's scope — surface it back to the user as a manual next step
(e.g. `gh repo create <org>/domo-client-template-business --private
--source=. --push`) and let them decide when to do it, rather than
performing it as part of this plan.
