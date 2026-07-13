# Domo Business-User Template — Design

**Date:** 2026-07-13
**Status:** Approved, ready for implementation planning

## Problem

`domo-client-template` (this repo) is built for Clearsquare's technical
coworkers: setup assumes comfort with git, terminal, `.env` files, and
GitHub templates. Clearsquare wants a version of this product usable
directly by a **non-technical business user at a Domo client** — someone
who can install a desktop app but has never touched a terminal, git, or
edited a config file.

Capability should not shrink: the business-user version needs the same
read/write Domo access (via the existing skills and CLAUDE.md safety
rules) as the technical template. Only the *onboarding path* needs to
change.

## Audience & constraints

- Business user can install a desktop application (e.g. Claude Code
  Desktop) but has zero terminal or git experience.
- Delivery is manual per engagement: Clearsquare zips a configured copy
  of the template and sends it to the client contact — there is no
  GitHub template flow, no `git clone`, no repo access for the client.
- The business user, not Clearsquare, generates their own Domo access
  token (Clearsquare doesn't reliably have admin access to every
  client's instance).
- Full feature parity with the technical template is required:
  dataset schema/query skills, dataflow read+edit, custom app building,
  and the existing write-permission / pre-flight-briefing safety rules
  in CLAUDE.md all carry over unchanged.

## Repo strategy

Create a new sibling repo, **`domo-client-template-business`**, seeded
from the current state of `domo-client-template`. It gets a fresh git
history (no shared history/merges with the technical repo — the two
products diverge in onboarding only and won't be merged back together).
Clearsquare maintains it independently going forward, the same way the
technical template is maintained today.

Everything that isn't onboarding-related carries over unchanged:
- `.claude/skills/` — all four Domo skills
  (`domo-get-dataset-schema`, `domo-query-dataset`, `domo-dataflow`,
  `domo-apps`)
- `apps/`, `manual/`, `qa/` folder structure
- CLAUDE.md's API Implementation Rules and Write Permission /
  Pre-Write Briefing rules

## First-run setup flow

A new skill, `.claude/skills/domo-first-run-setup/`, replaces the
manual `SETUP.md` steps with a conversational flow run by Claude
itself, inside the chat, using its own tool access (Bash/Edit) — the
business user never opens a terminal or edits a file directly.

**Trigger:** A new instruction near the top of `CLAUDE.md`, loaded
automatically at the start of every session:

> Before addressing anything else the user asks, check whether `.env`
> exists and has non-placeholder values for both `DOMO_INSTANCE` and
> `DOMO_ACCESS_TOKEN`. If not, invoke the `domo-first-run-setup` skill
> before doing anything else.

Because this lives in CLAUDE.md, it fires the moment the business user
opens the folder in Claude Code Desktop and sends any first message —
no separate command to remember.

**Flow:**
1. Ask for their Domo instance URL (e.g. `acme.domo.com`).
2. Walk them step-by-step, in plain language, through generating an
   access token in their own Domo instance: **Admin > Authentication >
   Access Tokens > Generate new token**. Ask them to paste the token
   into the chat.
3. Claude creates `.env` from `.env.example` and writes both values
   itself.
4. Claude runs the existing connectivity check
   (`GET /api/content/v2/users/me` with the token header). On success,
   confirms readiness and suggests example prompts to try. On a 401,
   explains in plain terms whether the instance or the token looks
   wrong, and asks the user to recheck — no raw curl/HTTP error dumped
   into the chat.
5. **Mid-session expiry:** if a 401 shows up later during normal use,
   Claude recognizes it and re-invokes the same skill to collect a
   fresh token, rather than failing silently or asking the user to
   debug it themselves.

## Documentation changes

- **`README.md` / `SETUP.md`**: rewritten for a non-technical reader.
  Drop all git/GitHub-template/terminal instructions. Replacement
  content: install Claude Code Desktop, unzip the folder Clearsquare
  sent, open it in Claude Code Desktop, start chatting — setup happens
  conversationally via the skill above.
- **`CLAUDE.md`**: keep the API Implementation Rules, safety/write-
  permission rules, and skills table unchanged — this content is
  guidance for Claude, not the end user. Add the first-run trigger
  instruction (see above) near the top.
- **Drop the CLI/SID fallback auth path** from CLAUDE.md. It requires
  `python3` and an interactive `domo login` in a terminal, which
  doesn't fit a zero-terminal user. Developer-token auth is the only
  supported path in this template. If a specific client instance can't
  mint an access token, that's resolved by Clearsquare before zipping,
  not something the business user handles.
- **`Context for this Project`** section of CLAUDE.md: filled in by
  Clearsquare per engagement before zipping, same as the technical
  template today.

## Distribution workflow

Per engagement, on Clearsquare's side:
1. Clone `domo-client-template-business` fresh.
2. Fill in the `Context for this Project` section of `CLAUDE.md` for
   the specific client (name, industry, engagement goal, data
   sources).
3. Zip the folder, excluding `.git`.
4. Send the zip to the business user with one instruction: unzip it,
   install/open Claude Code Desktop, open the folder, and start
   chatting.

## Out of scope

- No changes to skill capability or the underlying Domo API patterns —
  this is an onboarding/UX change only.
- No support for the business user regenerating or rotating the repo
  itself (e.g. pulling updates) — each engagement is a point-in-time
  zip snapshot from Clearsquare.
- No GitHub access, git literacy, or template-repo flow for the
  business user.
