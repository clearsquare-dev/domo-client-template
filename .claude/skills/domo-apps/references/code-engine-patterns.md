# Code Engine Patterns

Domo Code Engine provides serverless function execution within your Domo instance. Functions can be invoked from Custom Apps via `packageMapping`, from workflows, or via direct API calls. This reference covers function signatures, templates, lifecycle management, and integration with Custom Apps.

## Function Signatures

### Input Types

| Type | Usage | Common Use |
|------|-------|------------|
| `text` | Most common | IDs, names, SQL queries, JSON strings, URLs |
| `number` | Integers | User IDs, counts, numeric parameters |
| `decimal` | Floating point | Currency amounts, math operations |
| `object` | Complex structures | Request bodies, config objects |
| `boolean` | Flags | Toggle options, success indicators |
| `dataset` | Dataset reference | Dataset ID picker in Domo UI |
| `person` | User reference | User picker in Domo UI |
| `ACCOUNT` | Account credentials | OAuth tokens for external integrations — resolves via `codeengine.getAccount()` |
| `FILE` | File reference | File upload in Domo UI |

Use `isList: true` on any type to accept or return arrays.

### Output Types

| Type | Usage |
|------|-------|
| `object` | Structured API responses, complex results (most common) |
| `text` | String results, formatted output |
| `boolean` | Success/failure indicators |

### Function Manifest Entry

Every function needs a manifest entry with `name`, `displayName`, `description`, `inputs[]`, and `output`:

```json
{
  "name": "functionName",
  "displayName": "Human Readable Name",
  "description": "What this function does",
  "inputs": [
    {
      "name": "paramName",
      "displayName": "Parameter Label",
      "type": "text",
      "nullable": true,
      "isList": false
    }
  ],
  "output": {
    "name": "result",
    "displayName": "Result Label",
    "type": "object",
    "nullable": false,
    "isList": false
  }
}
```

## JavaScript Templates

### Template 1: Internal Domo API Helper

The most common pattern for packages that call internal Domo APIs. Uses `codeengine.sendRequest()` which runs in the context of your Domo instance — no authentication needed.

```javascript
const codeengine = require('codeengine');

class Helpers {
  static async handleRequest(method, url, body = null, headers = {}) {
    const res = await codeengine.sendRequest(method, url, body, { headers });
    if (res.status >= 400) throw new Error(`${method} ${url}: ${res.status}`);
    return res.body ? JSON.parse(res.body) : null;
  }
}

async function getDataSetMetadata(dataSetId) {
  const url = `api/data/v3/datasources/${dataSetId}?part=core,permission,status`;
  return Helpers.handleRequest('get', url);
}

async function queryDataset(datasetId, sql) {
  const url = `api/query/v1/execute/${datasetId}`;
  return Helpers.handleRequest('POST', url, { sql });
}

async function addOwnerToDataset(dataset, owner) {
  const url = `api/data/v1/datasources/${dataset}/owners/${owner}`;
  try {
    await Helpers.handleRequest('put', url);
    return true;
  } catch {
    return false;
  }
}

module.exports = { getDataSetMetadata, queryDataset, addOwnerToDataset };
```

**Manifest:**
```json
[
  {
    "name": "getDataSetMetadata",
    "displayName": "Get DataSet Metadata",
    "inputs": [{ "name": "dataSetId", "type": "text" }],
    "output": { "name": "result", "type": "object" }
  },
  {
    "name": "queryDataset",
    "displayName": "Query Dataset",
    "inputs": [
      { "name": "datasetId", "type": "dataset" },
      { "name": "sql", "type": "text" }
    ],
    "output": { "name": "result", "type": "object" }
  },
  {
    "name": "addOwnerToDataset",
    "displayName": "Add Owner To Dataset",
    "inputs": [
      { "name": "dataset", "type": "dataset" },
      { "name": "owner", "type": "person" }
    ],
    "output": { "name": "result", "type": "boolean" }
  }
]
```

### Template 2: External API with ACCOUNT Auth

For integrations with external services (Okta, AirTable, MS Graph, Google Sheets, etc.). The `ACCOUNT` type stores OAuth credentials that you resolve with `codeengine.getAccount()`.

```javascript
const codeengine = require('codeengine');
const axios = require('axios');

async function listRecords(account, baseId, tableId) {
  const acc = await codeengine.getAccount(account.id);
  const res = await axios.get(
    `https://api.airtable.com/v0/${baseId}/${tableId}`,
    { headers: { Authorization: `Bearer ${acc.properties.apikey}` } }
  );
  return res.data;
}

async function createRecord(account, baseId, tableId, fields) {
  const acc = await codeengine.getAccount(account.id);
  const res = await axios.post(
    `https://api.airtable.com/v0/${baseId}/${tableId}`,
    { fields },
    {
      headers: {
        Authorization: `Bearer ${acc.properties.apikey}`,
        'Content-Type': 'application/json',
      },
    }
  );
  return res.data;
}

module.exports = { listRecords, createRecord };
```

**Manifest:**
```json
[
  {
    "name": "listRecords",
    "displayName": "List Records",
    "inputs": [
      { "name": "account", "type": "ACCOUNT" },
      { "name": "baseId", "type": "text" },
      { "name": "tableId", "type": "text" }
    ],
    "output": { "name": "result", "type": "object" }
  },
  {
    "name": "createRecord",
    "displayName": "Create Record",
    "inputs": [
      { "name": "account", "type": "ACCOUNT" },
      { "name": "baseId", "type": "text" },
      { "name": "tableId", "type": "text" },
      { "name": "fields", "type": "object" }
    ],
    "output": { "name": "result", "type": "object" }
  }
]
```

### Template 3: Dataset SQL Query

Direct SQL querying against Domo datasets.

```javascript
const codeengine = require('codeengine');

async function queryWithSql(datasetId, sql) {
  const res = await codeengine.sendRequest(
    'POST',
    `api/query/v1/execute/${datasetId}`,
    { sql }
  );
  return JSON.parse(res.body);
}

async function queryDatasetAndFlattenField(datasetId, field) {
  const sql = `SELECT ${field} FROM table`;
  const rows = await queryWithSql(datasetId, sql);
  return [...new Set(rows.map((item) => item[field]))];
}

module.exports = { queryWithSql, queryDatasetAndFlattenField };
```

### Template 4: Email & Notifications

```javascript
const codeengine = require('codeengine');

function sendEmailToEmailAddress(subject, message, emailAddress) {
  const body = {
    parameters: {
      subject: subject,
      text: message,
      recipientsUserIds: [],
    },
  };
  const url = `/api/social/v3/messages/plainText/send?route=recipients&method=EMAIL&recipients=${emailAddress}`;

  return codeengine
    .sendRequest('post', url, body, null, null)
    .then(() => true)
    .catch((reason) => {
      console.log(reason);
      return false;
    });
}

function sendBuzzMessage(channelId, message) {
  const body = {
    domoSystemId: 'CARD',
    botRef: null,
    content: { text: message, tags: [] },
  };
  const url = `api/buzz/v1/channels/${channelId}/messages?mentionsGrantPermission=true`;

  codeengine.sendRequest('post', url, body, null, null).catch(console.log);
  return true;
}

module.exports = { sendEmailToEmailAddress, sendBuzzMessage };
```

## Python Templates

### Template 5: Python External API

```python
import codeengine
import requests

def get_file_set(base_url, file_set_id, developer_token):
    url = f"https://{base_url}/api/files/v1/filesets/{file_set_id}"
    headers = {"X-DOMO-Developer-Token": developer_token}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

def upload_file_to_set(base_url, file_set_id, file_name, file_content, developer_token):
    url = f"https://{base_url}/api/files/v1/filesets/{file_set_id}/files"
    headers = {
        "X-DOMO-Developer-Token": developer_token,
        "Content-Type": "application/octet-stream",
        "X-DOMO-File-Name": file_name,
    }
    response = requests.post(url, headers=headers, data=file_content, timeout=30)
    response.raise_for_status()
    return response.json()
```

### Template 6: Python Utilities

```python
def add(a: float, b: float) -> float:
    if a is None or b is None:
        raise ValueError("Parameters 'a' and 'b' are required")
    return float(a) + float(b)

def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Division by zero is not allowed")
    return float(a) / float(b)
```

**Python notes:**
- Functions prefixed with `_` are treated as private helpers and should NOT appear in the manifest
- Use `snake_case` for function names (JS uses `camelCase`)

## Package Lifecycle

### States

| State | Description |
|-------|-------------|
| `DRAFT` | Editable, not callable via public endpoint |
| `RELEASED` | Immutable, live and callable |

### Create → Release Flow

```
1. codeengine_package_create(        # Creates package + v1 in DRAFT
     name, description, code, functions
   )
2. Test the draft version             # Verify code compiles and logic is correct
3. codeengine_version_release(        # Release makes it live
     package_id, version=1
   )
4. codeengine_package_get(            # Verify deployment
     package_id
   )
```

### Update Flow

Released versions cannot be modified. To update:

```
1. codeengine_version_create(         # Creates v(N+1) in DRAFT
     package_id, updated_code, functions
   )
2. Test the new draft
3. codeengine_version_release(        # Release the new version
     package_id, version=N+1
   )
```

The latest released version becomes the default. Previous versions remain accessible.

## Wiring Code Engine to Custom Apps

### Package Mappings in manifest.json

To call a Code Engine function from your Custom App, add a `packageMapping` entry:

```json
{
  "packageMapping": [
    {
      "alias": "sendEmail",
      "parameters": [
        {
          "alias": "params",
          "type": "object",
          "nullable": false,
          "isList": false,
          "children": null
        }
      ],
      "output": {
        "alias": "returnValue",
        "type": "object",
        "children": null
      }
    }
  ]
}
```

### Calling from App Code

Use `ryuu.js` to call the mapped function:

```typescript
import domo from 'ryuu.js';

const CODE_ENGINE_BASE_URL = '/domo/codeengine/v2/packages';

// Call the mapped function by alias
const sendEmail = async (to: string, subject: string, body: string) => {
  const { returnValue } = await domo.post<{
    returnValue: { statusCode: number; payload: string };
  }>(`${CODE_ENGINE_BASE_URL}/sendEmail`, {
    params: { to, subject, body },
  });

  if (returnValue.statusCode !== 200) {
    throw new Error('Email cannot be sent');
  }

  return returnValue;
};
```

### Complete Wiring Example

**1. Create the Code Engine function:**
```
codeengine_package_create(
  name: "my-app-backend",
  description: "Backend functions for my custom app",
  code: "<the JavaScript code>",
  functions: [
    {
      name: "processOrder",
      displayName: "Process Order",
      inputs: [{ name: "params", type: "object" }],
      output: { name: "result", type: "object" }
    }
  ]
)
```

**2. Release the function:**
```
codeengine_version_release(package_id, version=1)
```

**3. Add to manifest.json:**
```json
{
  "packageMapping": [
    {
      "alias": "processOrder",
      "parameters": [
        { "alias": "params", "type": "object", "nullable": false, "isList": false, "children": null }
      ],
      "output": { "alias": "returnValue", "type": "object", "children": null }
    }
  ]
}
```

**4. Call from your app:**
```typescript
const processOrder = async (orderData: OrderInput) => {
  const { returnValue } = await domo.post(
    `${CODE_ENGINE_BASE_URL}/processOrder`,
    { params: orderData }
  );
  return returnValue;
};
```

## Error Handling Patterns

### JavaScript

```javascript
// Pattern 1: Helper class with status check (recommended)
class Helpers {
  static async handleRequest(method, url, body = null, headers = {}) {
    const res = await codeengine.sendRequest(method, url, body, { headers });
    if (res.status >= 400) throw new Error(`${method} ${url}: ${res.status}`);
    return res.body ? JSON.parse(res.body) : null;
  }
}

// Pattern 2: Boolean return with .catch (simple operations)
return codeengine
  .sendRequest('post', url, body)
  .then(() => true)
  .catch((reason) => {
    console.log(reason);
    return false;
  });

// Pattern 3: Error object return (when callers need error details)
try {
  const res = await codeengine.sendRequest('delete', url);
  return { success: true };
} catch (err) {
  return { success: false, error: String(err.message || err) };
}

// Pattern 4: Input validation
if (!datasetId) throw new Error('datasetId is required');
```

### Python

```python
# Input validation
if not isinstance(param, str) or not param.strip():
    raise ValueError("param must be a non-empty string")

# HTTP with status check
response = requests.get(url, headers=headers, timeout=10)
response.raise_for_status()
return response.json()
```

## Core API Patterns

| Pattern | When to Use |
|---------|------------|
| `codeengine.sendRequest(method, url, body)` | Internal Domo API calls (no auth needed) |
| `codeengine.getAccount(account.id)` | Resolve ACCOUNT parameter for external integrations |
| `axios.get/post(url, { headers })` | External API calls (JS) |
| `requests.get(url, headers=headers)` | External API calls (Python) |

## Naming Conventions

**Packages:** Use descriptive names
- Platform utilities: "DOMO DataSets", "DOMO Math"
- Workflows: "WorkflowBuilderBackend", "User Offboarding"
- Connectors: "Okta Connector", "AirTable Integration"

**Functions:**
- JavaScript: `camelCase` — `queryDatasetAndFlattenField`, `sendEmailToEmailAddress`
- Python: `snake_case` — `get_spreadsheet_metadata`, `get_file_set`
- Common verb prefixes: `get*`, `query*`, `send*`, `create*`, `add*`, `filter*`, `convert*`

## MCP Automation

The `domo-codeengine` MCP server provides 11 tools for managing the full lifecycle:

| Task | Tool |
|------|------|
| List all packages | `codeengine_package_list` |
| Get package details | `codeengine_package_get` |
| Create new package | `codeengine_package_create` |
| Update package info | `codeengine_package_update` |
| Delete a package | `codeengine_package_delete` |
| Get version code | `codeengine_version_get` |
| Create new version | `codeengine_version_create` |
| Update version | `codeengine_version_update` |
| Delete draft version | `codeengine_version_delete` |
| Release a version | `codeengine_version_release` |
| Check connectivity | `codeengine_health_check` |

## Best Practices

1. **Always release after testing** — Draft versions are not accessible externally
2. **Never modify released versions** — Create a new version instead
3. **Use the Helper class pattern** for packages with multiple Domo API functions
4. **Handle errors explicitly** — Unhandled exceptions produce unhelpful 500 responses
5. **Keep functions small** — Code Engine has execution time limits
6. **Use `codeengine.sendRequest()` for internal calls** — No auth needed, runs in instance context
7. **Use `codeengine.getAccount()` for external integrations** — Resolves stored OAuth credentials
8. **Validate inputs early** — Check required parameters at function entry
9. **Use `module.exports = { func1, func2 }` pattern** — Named export object at the bottom
10. **Plan for multiple versions** — Mature packages iterate heavily; the update flow is normal
