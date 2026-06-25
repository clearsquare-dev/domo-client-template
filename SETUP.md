# Setup — New Domo Client Workspace

This repo is a **GitHub template**. To start a new client engagement:

## 1. Create the client repo
Click **Use this template** on the GitHub repo page → create a new repo named for
the client.

## 2. Configure the environment
```bash
cp .env.example .env
```
Then edit `.env`:
- `DOMO_INSTANCE` → the client's instance host (e.g. `acme.domo.com`, no `https://`).
- `DOMO_ACCESS_TOKEN` → generate in Domo: **Admin > Authentication > Access
  Tokens**, then paste here.

## 3. Verify connectivity
```bash
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); fi
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://$DOMO_INSTANCE/api/content/v2/users/me" \
  -H "X-DOMO-Developer-Token: $DOMO_ACCESS_TOKEN"
```
Expect `200`. A `401` means the token or instance is wrong.

## 4. Customize CLAUDE.md
Fill in the **Context for this Project** section at the bottom of `CLAUDE.md`
(client name, industry, engagement goal, data sources).

## 5. (Optional) Per-source instances
Uncomment and set extra vars in `.env` as needed, e.g.
`FIELDROUTES_INSTANCE=...`.

---

### What's already wired up
- The four Domo skills under `.claude/skills/` — Claude Code auto-discovers them,
  no install needed.
- Token-first auth (no Python / `jq` required). A SID fallback is documented in
  `CLAUDE.md` for instances without a token.
- `.env`, `.venv/`, `.domo_cli/`, and `.idea/` are gitignored.
