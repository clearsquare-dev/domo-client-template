# Manifest Configuration Guide

The `manifest.json` file is the core configuration for your Domo App.

## Basic Structure

```json
{
  "name": "My App",
  "version": "1.0.0",
  "size": {
    "width": 5,
    "height": 3
  },
  "fullpage": true,
  "id": "app-uuid",           // Added after first publish
  "proxyId": "proxy-uuid",    // Required if using AppDB
  "mapping": [],
  "collections": [],
  "packageMapping": []
}
```

## App Metadata

- **name** - Display name of the app
- **version** - Semantic version (1.0.0)
- **size** - Grid dimensions (width/height 1-12)
- **fullpage** - Boolean, if true app takes full page
- **id** - App UUID (copy from build/manifest.json after first publish)
- **proxyId** - Only required when using AppDB collections. NOT needed for dataset queries — `domo dev` handles those via the authenticated CLI session.

## Data Mappings

Connect Domo datasets to your app with aliases for easy access.

### Simple Mapping (No Field Aliases)

When you want all dataset fields without renaming:

```json
{
  "mapping": [
    {
      "dataSetId": "e1fa8ac3-4832-447b-8483-7b22adb63feb",
      "alias": "EntryData",
      "fields": []
    }
  ]
}
```

### Field-Level Mapping

Map specific fields with custom aliases:

```json
{
  "mapping": [
    {
      "dataSetId": "c55d1d5e-7b7b-481c-b4be-90dc03f605c9",
      "alias": "DataSourceRegistry",
      "fields": [
        {
          "alias": "WorkItemType",
          "columnName": "WorkItemType"
        },
        {
          "alias": "DataSetId",
          "columnName": "DataSetId"
        }
      ]
    }
  ]
}
```

### Real-World Example: Multiple Dataset Mappings

```json
{
  "mapping": [
    {
      "dataSetId": "d4a91906-d903-474e-ae4d-37713bc582d1",
      "alias": "DetailTabs",
      "fields": [
        {
          "alias": "WorkItemType",
          "columnName": "Work_Item_Type"
        },
        {
          "alias": "TabName",
          "columnName": "Tab_Name"
        },
        {
          "alias": "Order",
          "columnName": "Order"
        },
        {
          "alias": "Placement",
          "columnName": "Placement"
        }
      ]
    },
    {
      "dataSetId": "1c77faca-707d-4472-9079-c006635127fa",
      "alias": "CoreFields",
      "fields": [
        {
          "alias": "WorkItemType",
          "columnName": "Work_Item_Type"
        },
        {
          "alias": "GridMapping",
          "columnName": "Grid_Mapping"
        },
        {
          "alias": "FieldName",
          "columnName": "Field_Name"
        },
        {
          "alias": "FieldLabel",
          "columnName": "Field_Label"
        }
      ]
    }
  ]
}
```

**Usage in code:**
```typescript
import Query from '@domoinc/query';
import { SqlClient } from '@domoinc/toolkit';

// Query dataset by alias using Query class
const data = await new Query()
  .select(['WorkItemType', 'TabName', 'Order', 'Placement'])
  .fetch('DetailTabs');

// Using SqlClient with filtering
const query = `
  SELECT "WorkItemType", "FieldName", "FieldLabel"
  FROM table
  WHERE "WorkItemType" = 'Invoice'
`;
const { data: result } = await new SqlClient().get('CoreFields', query);
```

## Collections (AppDB)

AppDB provides local database storage for your app with fine-grained permissions.

### Basic Collection

```json
{
  "collections": [
    {
      "name": "MyCollection",
      "syncEnabled": true,
      "schema": {
        "columns": [
          {
            "name": "fieldName",
            "type": "STRING"
          },
          {
            "name": "count",
            "type": "STRING"
          },
          {
            "name": "createdDate",
            "type": "STRING"
          }
        ]
      },
      "defaultPermission": [
        "READ",
        "READ_CONTENT",
        "CREATE_CONTENT"
      ]
    }
  ]
}
```

### Collection with Filters

Restrict access using filters (commonly used for owner-based access):

```json
{
  "collections": [
    {
      "name": "EXM_Files_Details",
      "syncEnabled": true,
      "schema": {
        "columns": [
          {
            "name": "fileId",
            "type": "STRING"
          },
          {
            "name": "name",
            "type": "STRING"
          },
          {
            "name": "UID",
            "type": "STRING"
          },
          {
            "name": "uploadedBy",
            "type": "STRING"
          }
        ]
      },
      "defaultPermission": [
        "READ",
        "READ_CONTENT",
        "CREATE_CONTENT",
        "UPDATE_CONTENT",
        "DELETE_CONTENT"
      ],
      "filters": [
        {
          "name": "File_Deletion_Filter",
          "applyOn": ["DELETE", "UPDATE"],
          "applyTo": [],
          "applyToAll": true,
          "limitToOwner": true,
          "query": {}
        }
      ]
    }
  ]
}
```

**What this does:** Users can read all files, but can only UPDATE or DELETE files they created (limitToOwner: true).

### Real-World Example: Audit Log Collection

```json
{
  "collections": [
    {
      "name": "EXM_Audit_Log",
      "syncEnabled": true,
      "schema": {
        "columns": [
          {
            "name": "entryId",
            "type": "STRING"
          },
          {
            "name": "UID",
            "type": "STRING"
          },
          {
            "name": "field",
            "type": "STRING"
          },
          {
            "name": "value",
            "type": "STRING"
          }
        ]
      },
      "defaultPermission": [
        "READ",
        "READ_CONTENT",
        "CREATE_CONTENT"
      ]
    }
  ]
}
```

**Usage in code:**
```typescript
import { AppDBClient } from '@domoinc/toolkit';

interface LogEntry {
  entryId: string;
  UID: string;
  field: string;
  value: string;
}

// Create typed client
const AuditLogClient = new AppDBClient.DocumentsClient<LogEntry>(
  'EXM_Audit_Log'
);

// Read from collection
const response = await AuditLogClient.get({}, {});
const logs = response.data;

// Create document
await AuditLogClient.create({
  entryId: '123',
  UID: 'user-456',
  field: 'status',
  value: 'completed'
});

// Query with filter
const queryParams = { 'content.UID': { $eq: 'user-456' } };
const filtered = (await AuditLogClient.get(queryParams, {})).data;
```

### Document Structure

AppDB documents have this structure:

```typescript
{
  "id": "1742e635-2346-42a9-a6ce-54c28880a650",          // Auto-generated document ID
  "datastoreId": "debfdc54-92a6-413e-8e62-6d6a96329b5c", // Datastore ID
  "collectionId": "4f2fc6c9-dac8-45c1-8416-b190f0a7986a", // Collection ID
  "syncRequired": true,                                   // Sync status
  "owner": "812268184",                                   // Owner user ID
  "createdBy": "812268184",                               // Creator user ID
  "createdOn": "2025-10-30T21:37:57.335Z",               // Creation timestamp
  "updatedOn": "2025-10-30T21:37:57.335Z",               // Last update timestamp
  "updatedBy": "812268184",                               // Last updater ID
  "content": {                                            // Your data
    "snowflake_database": "test",
    "snowflake_schema": "test",
    "snowflake_role": "test",
    "snowflake_warehouse": "test",
    "snowflake_view": "test"
  }
}
```

### Column Types

**IMPORTANT:** Always use `STRING` for all column types. Other types (`NUMBER`, `BOOLEAN`, `DATE`) are **not supported** by the Domo AppDB API and will cause publish errors. Store all values as strings and convert in your application code.

### Permissions

- **READ** - List documents in collection
- **READ_CONTENT** - Read document content
- **CREATE_CONTENT** - Insert new documents
- **UPDATE_CONTENT** - Modify existing documents
- **DELETE_CONTENT** - Remove documents

### Filter Configuration

- **name** - Filter identifier
- **applyOn** - Operations to filter: ["READ", "UPDATE", "DELETE", "CREATE"]
- **applyTo** - Specific users/groups (empty = all users)
- **applyToAll** - Apply to all users (true/false)
- **limitToOwner** - Restrict to document owner (true/false)
- **query** - MongoDB-style query filter

## Package Mappings

Call external Domo functions like workflows, email services, etc.

### Real-World Example: Email and Workflow Integration

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
    },
    {
      "alias": "getFile",
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
    },
    {
      "alias": "invokeWorkflow",
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

**Usage in code:**
```typescript
import domo from 'ryuu.js';

const CODE_ENGINE_BASE_URL = '/domo/codeengine/v2/packages';

// Send email via package
const { returnValue } = await domo.post(`${CODE_ENGINE_BASE_URL}/sendEmail`, {
  params: {
    to: 'user@example.com',
    subject: 'Notification',
    body: 'Your request has been processed'
  }
});

// Invoke workflow
const { returnValue: workflowResult } = await domo.post(
  `${CODE_ENGINE_BASE_URL}/invokeWorkflow`,
  {
    params: {
      workflowId: 'workflow-uuid',
      workflowVersion: '1',
      workflowParams: {
        action: 'approve',
        recordId: '12345'
      }
    }
  }
);

// Get file
const { returnValue: file } = await domo.post(`${CODE_ENGINE_BASE_URL}/getFile`, {
  params: {
    fileId: 'file-uuid'
  }
});
```

## Environment Overrides

Use `src/manifestOverrides.json` for environment-specific configurations.

### Real-World Example: Multi-Environment Setup

```json
{
  "domo-es.dev": {
    "description": "Development Environment",
    "manifest": {
      "name": "MyApp - DEV",
      "id": "e255f923-6939-40c2-8848-c392beaaa224",
      "proxyId": "7c5ed084-6684-4179-91f8-283fcd159381"
    }
  },
  "domo-es.uat": {
    "description": "UAT Environment",
    "manifest": {
      "name": "MyApp - UAT",
      "id": "147f25a6-6ba1-4604-9749-dc8d93068c62",
      "proxyId": "6b1836b9-a7b5-4397-86c9-c77a92a9abed"
    }
  },
  "production": {
    "description": "Production Environment",
    "manifest": {
      "name": "MyApp",
      "id": "397d9161-12fd-42da-948c-c08cb29d1903"
    }
  }
}
```

### Apply with Build Scripts

**package.json:**
```json
{
  "scripts": {
    "prestart": "da apply-manifest start",
    "postbuild": "da apply-manifest build",
    "build:dev": "GENERATE_SOURCEMAP=false react-scripts build",
    "postbuild:dev": "da apply-manifest build \"domo-es.dev\"",
    "build:uat": "GENERATE_SOURCEMAP=false react-scripts build",
    "postbuild:uat": "da apply-manifest build \"domo-es.uat\"",
    "build:prod": "GENERATE_SOURCEMAP=false react-scripts build",
    "postbuild:prod": "da apply-manifest build production"
  }
}
```

### Override Dataset IDs by Environment

```json
{
  "dev": {
    "description": "Development datasets",
    "manifest": {
      "mapping": [
        {
          "dataSetId": "dev-dataset-uuid-111",
          "alias": "Users"
        },
        {
          "dataSetId": "dev-dataset-uuid-222",
          "alias": "Orders"
        }
      ]
    }
  },
  "prod": {
    "description": "Production datasets",
    "manifest": {
      "mapping": [
        {
          "dataSetId": "prod-dataset-uuid-333",
          "alias": "Users"
        },
        {
          "dataSetId": "prod-dataset-uuid-444",
          "alias": "Orders"
        }
      ]
    }
  }
}
```

**Usage:**
```bash
# Development build
yarn build:dev
# Applies "dev" overrides

# Production build
yarn build:prod
# Applies "prod" overrides
```

## Complete Real-World Example

Here's a complete manifest from a production app:

```json
{
  "name": "US Bank Exception Management",
  "version": "3.16.2",
  "size": {
    "width": 5,
    "height": 3
  },
  "fullpage": true,
  "mapping": [
    {
      "dataSetId": "c55d1d5e-7b7b-481c-b4be-90dc03f605c9",
      "alias": "DataSourceRegistry",
      "fields": [
        {
          "alias": "WorkItemType",
          "columnName": "WorkItemType"
        },
        {
          "alias": "DataSetId",
          "columnName": "DataSetId"
        }
      ]
    },
    {
      "dataSetId": "5fa65e72-aba7-4638-8c97-444e92e828ef",
      "alias": "Owners",
      "fields": [
        {
          "alias": "WorkItemType",
          "columnName": "Work_Item_Type"
        },
        {
          "alias": "Name",
          "columnName": "Member_Name"
        },
        {
          "alias": "Email",
          "columnName": "Member_Email"
        },
        {
          "alias": "Team",
          "columnName": "Assigned_Team"
        }
      ]
    }
  ],
  "collections": [
    {
      "name": "EXM_Comments",
      "syncEnabled": true,
      "schema": {
        "columns": [
          {
            "name": "UID",
            "type": "STRING"
          },
          {
            "name": "userEmail",
            "type": "STRING"
          },
          {
            "name": "userName",
            "type": "STRING"
          },
          {
            "name": "body",
            "type": "STRING"
          },
          {
            "name": "attachment",
            "type": "STRING"
          },
          {
            "name": "systemGenerated",
            "type": "STRING"
          }
        ]
      },
      "defaultPermission": [
        "READ",
        "READ_CONTENT",
        "CREATE_CONTENT"
      ]
    }
  ],
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
    },
    {
      "alias": "invokeWorkflow",
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

## Required Fields After First Publish

After your first `domo publish`, you MUST copy these fields from `build/manifest.json` to `public/manifest.json`:

1. **id** - App UUID (prevents creating new app on each upload)
2. **proxyId** - Required if using AppDB collections

**Workflow:**
```bash
# First publish
yarn build
cd build && domo publish && cd ..

# Copy the generated id and proxyId
cat build/manifest.json  # Find "id" and "proxyId"

# Add to public/manifest.json
# Now future publishes update the same app
```

## Best Practices

1. **Version Control** - Always commit manifest.json to git
2. **Environment Separation** - Use manifestOverrides.json for env-specific configs
3. **App ID Management** - Copy id from build to public after first publish to prevent duplicate apps
4. **ProxyId Required** - If using AppDB, you MUST have proxyId in manifest
5. **Schema Design** - Plan AppDB schemas carefully (migrations are difficult)
6. **Permissions** - Start restrictive, add permissions as needed
7. **Aliases** - Use descriptive, consistent aliases for data mappings
8. **Field Names** - Match schema column names exactly in collections
9. **Documentation** - Comment complex package mappings and workflows
10. **Testing** - Test manifest changes in dev environment first

## Common Issues

**Problem:** Each publish creates a new app
**Solution:** Copy `id` field from build/manifest.json to public/manifest.json

**Problem:** AppDB not working
**Solution:** Ensure `proxyId` is set in manifest.json

**Problem:** `domo dev` data queries fail / "domo is not defined"
**Solution:** For vanilla JS apps, add these scripts to `<head>` in `index.html`:
```html
<script src="https://cdn.domo.com/domo.js/1/domo.js"></script>
<script src="https://unpkg.com/ryuu.js@4.6.0/dist/domo.js"
  integrity="sha384-YYsd9wQ+wDlUWhvpfGdptxmNYIqBC+52oJtWgPKJadbs3sSFTY/+ZotPbEHTTRWz"
  crossorigin="anonymous"></script>
```
These are NOT included by `domo init` — you must add them manually.

**Problem:** SQL query returns error / empty data despite correct alias
**Solution:** Use `contentType: 'text/plain'` and pass SQL as a plain string — NOT a JSON object:
```js
// ✅ Correct
domo.post('/sql/v1/myAlias', 'SELECT col FROM table', { contentType: 'text/plain' })

// ❌ Wrong — will fail silently or return error
domo.post('/sql/v1/myAlias', { sql: 'SELECT col FROM table' }, { contentType: 'application/json' })
```
Rows come back as arrays (`row[0]`, `row[1]`), not objects.

**Problem:** Columns with dots in their names (e.g. `employee.fullName`) fail in SQL
**Solution:** Use backtick quoting, not double quotes:
```sql
SELECT \`employee.fullName\`, \`subscription.annualRecurringValue\` FROM table
```

**Problem:** Dataset not found in code
**Solution:** Check `alias` in mapping matches code reference

**Problem:** Permission denied on collection
**Solution:** Review `defaultPermission` and `filters` in collection config

**Problem:** Different data in different environments
**Solution:** Use manifestOverrides.json with environment-specific dataSetIds
