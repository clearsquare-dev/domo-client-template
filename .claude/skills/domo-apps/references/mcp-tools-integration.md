# MCP Tools Integration Guide

MCP (Model Context Protocol) tools let AI agents execute real API calls against your Domo instance. Instead of just documenting how to write code, the agent can actually create collections, query datasets, deploy functions, and publish apps — all through natural language.

## What Are MCP Tools?

MCP tools are structured API wrappers that run in the context of your Domo instance. Each MCP server provides a set of tools that map to Domo REST APIs. When you ask an agent to "create an AppDB collection for storing user preferences," the agent calls the appropriate MCP tool, which makes the actual API call to Domo and returns the result.

**Key difference from writing app code:**
- **App code** (using `@domoinc/toolkit`) runs inside your deployed app at runtime
- **MCP tools** run during development, letting the agent set up infrastructure, seed data, verify schemas, and validate configurations before you write any code

## Available MCP Servers

### domo-appdb — 12 tools

CRUD operations for AppDB collections and documents.

| Tool | Description |
|------|-------------|
| `appdb_collection_list` | List all AppDB collections |
| `appdb_collection_get` | Get a collection by ID |
| `appdb_collection_create` | Create a new AppDB collection |
| `appdb_collection_update` | Update a collection |
| `appdb_collection_delete` | Delete a collection |
| `appdb_document_list` | List documents in a collection |
| `appdb_document_get` | Get a document by ID |
| `appdb_document_create` | Create a document in a collection |
| `appdb_document_update` | Update a document |
| `appdb_document_delete` | Delete a document |
| `appdb_bulk_insert` | Insert multiple documents at once |
| `health_check` | Verify AppDB API connectivity |

**How this complements app development:** Instead of just defining collections in `manifest.json` and hoping the schema is right, the agent can create collections, insert sample documents, and verify the schema before you write any app code. This catches schema issues early.

### domo-datasets — 16 tools

Dataset and stream management.

| Tool | Description |
|------|-------------|
| `dataset_list` | List/search datasets |
| `dataset_get` | Get dataset details |
| `dataset_schema` | Get dataset schema (column names and types) |
| `dataset_query` | Execute SQL query against a dataset |
| `dataset_profile` | Profile columns with stats and classification |
| `dataset_create` | Create a new dataset |
| `dataset_update` | Update dataset metadata |
| `dataset_import_csv` | Upload CSV data to a dataset |
| `dataset_delete` | Delete a dataset |
| `dataset_schema_indexed` | Get indexed schema with column positions |
| `dataset_lineage` | Trace upstream/downstream data lineage |
| `stream_list` | List streams (data pipelines) |
| `stream_get` | Get stream details |
| `stream_executions` | Get stream execution history |
| `stream_lookup` | Find stream ID for a dataset |
| `health_check` | Verify Datasets API connectivity |

**How this complements app development:** When setting up data mappings in `manifest.json`, the agent can query the actual dataset to verify column names, check data types, and confirm the SQL patterns in your `@domoinc/query` calls will work. No more guessing at column names.

### domo-codeengine — 11 tools

Serverless function package management.

| Tool | Description |
|------|-------------|
| `codeengine_package_list` | List all Code Engine packages |
| `codeengine_package_get` | Get a package with its versions |
| `codeengine_package_create` | Create a new package with code |
| `codeengine_package_update` | Update package metadata |
| `codeengine_package_delete` | Delete a package |
| `codeengine_version_get` | Get version detail with code |
| `codeengine_version_create` | Create a new version with updated code |
| `codeengine_version_update` | Update version metadata and functions |
| `codeengine_version_delete` | Delete an unreleased version |
| `codeengine_version_release` | Release/publish a version |
| `codeengine_health_check` | Verify Code Engine API connectivity |

**How this complements app development:** Apps that use `packageMapping` in `manifest.json` depend on Code Engine functions being deployed and released. The agent can create the function, write the code, release it, and then wire it into your manifest — all in one workflow.

### domo-pages — 27 tools

Page, card, beast mode, and layout management.

| Tool | Description |
|------|-------------|
| `page_list` | List Domo pages with pagination |
| `page_get` | Get a single page by ID |
| `page_cards` | Get all cards on a page |
| `page_create` | Create a new page/dashboard |
| `page_update` | Update a page's title |
| `page_delete` | Delete a page |
| `card_create` | Create a KPI card |
| `card_create_full` | Create a fully configured card with columns, filters, groupBy, orderBy |
| `card_update` | Update a card's title/chart type |
| `card_delete` | Delete a card |
| `card_metadata` | Get card metadata |
| `card_definition` | Get full card definition with Beast Modes, columns, filters |
| `card_save` | Save modifications to a card definition |
| `card_preview` | Preview a card configuration as a rendered image |
| `card_bulk_definitions` | Get definitions for multiple cards at once |
| `card_size_set` | Set card sizes on a page |
| `card_render_check` | Verify a card renders correctly |
| `beast_mode_validate` | Validate a Beast Mode formula |
| `beast_mode_create` | Create Beast Mode calculated fields |
| `beast_mode_list` | List all Beast Modes on a dataset |
| `beast_mode_delete` | Delete Beast Mode calculated fields |
| `layout_get` | Get page layout (card positions on 60-unit grid) |
| `layout_convert` | Convert v1 dashboard to design layout |
| `layout_set` | Set card positions on a page layout grid |
| `app_card_create` | Place a Custom App on a page as a card |
| `app_card_list` | List all Custom App cards on a page |
| `health_check` | Verify Pages API connectivity |

**How this complements app development:** After building and publishing your custom app, the agent can place it on a dashboard page alongside native Domo cards, set the layout, and create a complete dashboard experience — all programmatically.

### domo-publish — 6 tools

Pro-Code app design management and publishing.

| Tool | Description |
|------|-------------|
| `procode_design_list` | List Pro-Code app designs with versions |
| `procode_source_download` | Download app source code for inspection |
| `procode_manifest_validate` | Validate manifest.json for common issues |
| `procode_publish` | Publish a Pro-Code app to Domo |
| `publication_list` | List Domo Everywhere publications |
| `health_check` | Verify Publish API connectivity |

**How this complements app development:** The agent can validate your `manifest.json` before publishing, catch common issues (wrong keys, missing fields, bad fileName references), and publish directly — eliminating the manual `cd build && domo publish` workflow.

### domo-search — 2 tools

Cross-entity search across Domo.

| Tool | Description |
|------|-------------|
| `search_query` | Search across pages, cards, datasets, users |
| `health_check` | Verify Search API connectivity |

**How this complements app development:** Find datasets by name, locate existing pages, or discover cards that already visualize the data your app needs.

### domo-users — 6 tools

User management.

| Tool | Description |
|------|-------------|
| `user_list` | List/search users with pagination |
| `user_get` | Get a single user by ID |
| `user_create` | Create a new user |
| `user_update` | Update an existing user |
| `user_delete` | Delete a user |
| `health_check` | Verify Users API connectivity |

**How this complements app development:** Verify user IDs for AppDB permission filters, look up user details for testing owner-based access patterns, or manage users in development instances.

## Integration Patterns

### After Scaffolding an App

**Workflow:** `da new` → MCP tools → code

After creating a new app with `da new`, use MCP tools to set up the infrastructure:

```
1. da new my-app                          # Scaffold the app
2. appdb_collection_create(...)           # Create AppDB collections
3. appdb_bulk_insert(...)                 # Seed with test data
4. dataset_schema(dataset_id)             # Verify dataset columns
5. Edit manifest.json                     # Wire up mappings with verified names
```

This ensures your collections exist and your dataset references are correct before writing any app code.

### Verifying Data Mappings

**Workflow:** `manifest.json` mapping → MCP verification

Before coding your data layer, verify everything:

```
1. dataset_list(name_contains="Sales")    # Find the right dataset
2. dataset_schema(dataset_id)             # Get exact column names
3. dataset_query(dataset_id, "SELECT ...")# Verify SQL works
4. Update manifest.json with verified IDs and aliases
```

This prevents the common "column not found" errors that only surface at runtime.

### Deploying Code Engine Functions

**Workflow:** Write function → MCP deploy → wire to manifest

For apps that use `packageMapping`:

```
1. codeengine_package_create(             # Create the function
     name: "my-email-handler",
     code: "...",
     functions: [...]
   )
2. codeengine_version_release(...)        # Release it
3. Add packageMapping to manifest.json    # Wire it to the app
4. procode_manifest_validate(...)         # Validate the manifest
```

### Publishing and Placing Apps

**Workflow:** Build → publish → place on dashboard

```
1. procode_manifest_validate(...)         # Validate before publish
2. procode_publish(...)                   # Publish to Domo
3. page_create(title="My Dashboard")      # Create a dashboard
4. app_card_create(designId, pageId)      # Place app on page
5. layout_set(pageId, positions)          # Position the card
```

### Full Development Cycle Example

Here's a complete workflow for building an app with AppDB, Code Engine, and dashboard integration:

```
# 1. Verify data sources
dataset_list(name_contains="Sales")
dataset_schema("dataset-uuid")
dataset_query("dataset-uuid", "SELECT DISTINCT Region FROM table LIMIT 10")

# 2. Create AppDB collections
appdb_collection_create(name="UserPreferences", schema={...})
appdb_bulk_insert(collection_id, [{userId: "test", theme: "dark"}])

# 3. Deploy Code Engine functions
codeengine_package_create(name="sales-notifications", code="...", functions=[...])
codeengine_version_release(package_id, version=1)

# 4. Validate and publish the app
procode_manifest_validate(manifest)
procode_publish(app_directory)

# 5. Create dashboard with the app
page_create(title="Sales Dashboard")
app_card_create(designId, pageId)
card_create_full(...)  # Add native cards alongside
layout_set(pageId, positions)
```

## Setup Instructions

### Configure MCP Servers in Claude Code

Add MCP servers to your `claude-mcp-config.json` (or `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "domo-appdb": {
      "command": "node",
      "args": ["/path/to/domo-appdb/server.js"],
      "env": {
        "DOMO_INSTANCE": "your-instance",
        "DOMO_DEVELOPER_TOKEN": "your-token"
      }
    },
    "domo-datasets": {
      "command": "node",
      "args": ["/path/to/domo-datasets/server.js"],
      "env": {
        "DOMO_INSTANCE": "your-instance",
        "DOMO_DEVELOPER_TOKEN": "your-token"
      }
    },
    "domo-codeengine": {
      "command": "node",
      "args": ["/path/to/domo-codeengine/server.js"],
      "env": {
        "DOMO_INSTANCE": "your-instance",
        "DOMO_DEVELOPER_TOKEN": "your-token"
      }
    },
    "domo-pages": {
      "command": "node",
      "args": ["/path/to/domo-pages/server.js"],
      "env": {
        "DOMO_INSTANCE": "your-instance",
        "DOMO_DEVELOPER_TOKEN": "your-token"
      }
    },
    "domo-publish": {
      "command": "node",
      "args": ["/path/to/domo-publish/server.js"],
      "env": {
        "DOMO_INSTANCE": "your-instance",
        "DOMO_DEVELOPER_TOKEN": "your-token"
      }
    },
    "domo-search": {
      "command": "node",
      "args": ["/path/to/domo-search/server.js"],
      "env": {
        "DOMO_INSTANCE": "your-instance",
        "DOMO_DEVELOPER_TOKEN": "your-token"
      }
    },
    "domo-users": {
      "command": "node",
      "args": ["/path/to/domo-users/server.js"],
      "env": {
        "DOMO_INSTANCE": "your-instance",
        "DOMO_DEVELOPER_TOKEN": "your-token"
      }
    }
  }
}
```

### Getting Your Developer Token

1. Go to **Domo Admin > Security > Access Tokens**
2. Create a new Developer Token
3. Copy the token string (starts with `DDCI...`)
4. Set it as `DOMO_DEVELOPER_TOKEN` in your config
5. Set `DOMO_INSTANCE` to your instance name (e.g., `company` for `company.domo.com`)

### Verifying Connectivity

After configuration, test each server:

```
health_check()  # Run on each MCP server
```

Each server has a `health_check` tool that verifies API connectivity and authentication.

## Best Practices

1. **Validate before publishing** — Always run `procode_manifest_validate` before `procode_publish`
2. **Verify schemas early** — Use `dataset_schema` to confirm column names before coding data queries
3. **Seed test data** — Use `appdb_bulk_insert` to populate collections with test data during development
4. **Preview cards** — Use `card_preview` to verify chart configurations before creating them
5. **Release Code Engine functions** — Draft versions are not callable; always release after testing
6. **Use search** — `search_query` helps find existing datasets and pages instead of creating duplicates
7. **Check health first** — Run `health_check` on each server before starting a workflow to catch auth issues early
